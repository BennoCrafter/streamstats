"""Prime Video implementation of StreamingService, reading the Amazon data export."""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from .base import BillingEvent, StreamingService, ViewingEvent

_PLACEHOLDERS = {"", "Not available", "Not Available"}


def _clean(value: str) -> Optional[str]:
    """Amazon's export wraps string fields in an extra layer of quotes; strip and nullify placeholders."""
    value = value.strip('"')
    return value if value not in _PLACEHOLDERS else None


class PrimeVideoService(StreamingService):
    name = "Prime Video"

    def __init__(self, export_root: Path):
        self.export_root = Path(export_root)

    def viewing_events(self) -> Iterator[ViewingEvent]:
        path = self.export_root / "Your Prime Video Viewing Activity" / "Viewing History.csv"
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                seconds = float(row["Seconds Viewed"])
                if seconds <= 0:
                    continue  # promo/autoplay impressions with no actual watch time
                yield ViewingEvent(
                    profile=_clean(row["Profile Type"]) or "unknown",
                    title=_clean(row["Title"]) or "unknown",
                    start_time=datetime.strptime(row["Playback Start Datetime (UTC)"], "%Y-%m-%dT%H:%M:%SZ"),
                    duration=timedelta(seconds=seconds),
                    device=_clean(row["Device Model"]),
                    country=_clean(row["Country Code"]),
                )

    def billing_events(self) -> Iterator[BillingEvent]:
        # Amazon's export has no price field for Prime Video: subscription cost is
        # billed at the Amazon-account level and purchases/rentals carry no amount.
        return iter(())
