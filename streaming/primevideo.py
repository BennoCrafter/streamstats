"""Prime Video implementation of StreamingService, reading the Amazon data export."""

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from .base import BillingEvent, StreamingService, ViewingEvent

_PLACEHOLDERS = {"", "Not available", "Not Available", "NOT AVAILABLE"}


def _clean(value: str) -> Optional[str]:
    """Amazon's export wraps string fields in an extra layer of quotes; strip and nullify placeholders."""
    value = value.strip('"')
    return value if value not in _PLACEHOLDERS else None


class PrimeVideoService(StreamingService):
    name = "Prime Video"

    def __init__(self, export_root: Path, monthly_price: Optional[float] = None, currency: str = "EUR"):
        self.export_root = Path(export_root)
        # Amazon's export has no price field for Prime Video (subscription cost is
        # billed at the Amazon-account level): configure a roundabout monthly price
        # to turn viewing activity into estimated billing events, or leave it unset.
        self.monthly_price = monthly_price
        self.currency = currency

    def viewing_events(self) -> Iterator[ViewingEvent]:
        activity = self.export_root / "Your Prime Video Viewing Activity"
        # (title, day) pairs already yielded - Watch Events re-lists titles Viewing
        # History also has (sometimes just as near-zero autoplay noise), so this has
        # to dedupe per watch occasion, not per title, or real rewatches get dropped.
        seen = set()

        path = activity / "Viewing History.csv"
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                seconds = float(row["Seconds Viewed"])
                if seconds <= 0:
                    continue  # promo/autoplay impressions with no actual watch time
                title = _clean(row["Title"]) or "unknown"
                start_time = datetime.strptime(row["Playback Start Datetime (UTC)"], "%Y-%m-%dT%H:%M:%SZ")
                seen.add((title, start_time.date()))
                yield ViewingEvent(
                    profile=_clean(row["Profile Type"]) or "unknown",
                    title=title,
                    start_time=start_time,
                    duration=timedelta(seconds=seconds),
                    device=_clean(row["Device Model"]),
                    country=_clean(row["Country Code"]),
                )

        # Watch Events carries one row per watch occasion per title - including
        # occasions Amazon has already pruned from Viewing History's session log -
        # but no profile/device/country. Only add occasions not already covered
        # above (same title, same day), so the same watch isn't counted twice.
        path = activity / "Watch Events.csv"
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if _clean(row["Deleted from Watch History"]) == "yes":
                    continue
                title = _clean(row["Title Name"]) or "unknown"
                seconds_raw = _clean(row["Seconds Watched"])
                if seconds_raw is None or float(seconds_raw) <= 0:
                    continue
                start_time = datetime.strptime(row["Most Recent Watch Date"], "%Y-%m-%dT%H:%M:%SZ")
                if (title, start_time.date()) in seen:
                    continue
                seen.add((title, start_time.date()))
                yield ViewingEvent(
                    profile="unknown",
                    title=title,
                    start_time=start_time,
                    duration=timedelta(seconds=float(seconds_raw)),
                )

    def billing_events(self) -> Iterator[BillingEvent]:
        if self.monthly_price is None:
            return
        months = sorted({(e.start_time.year, e.start_time.month) for e in self.viewing_events()})
        for year, month in months:
            yield BillingEvent(
                date=date(year, month, 1),
                amount=self.monthly_price,
                currency=self.currency,
                description="Prime Video subscription (estimated)",
            )
