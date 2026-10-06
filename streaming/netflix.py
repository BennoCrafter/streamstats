"""Netflix implementation of StreamingService, reading the official data export."""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from .base import BillingEvent, StreamingService, ViewingEvent


def _parse_duration(value: str) -> timedelta:
    """"HH:MM:SS" -> timedelta."""
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


class NetflixService(StreamingService):
    name = "Netflix"

    def __init__(self, export_root: Path):
        self.export_root = Path(export_root)

    def viewing_events(self) -> Iterator[ViewingEvent]:
        path = self.export_root / "CONTENT_INTERACTION" / "ViewingActivity.csv"
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                yield ViewingEvent(
                    profile=row["Profile Name"],
                    title=row["Title"],
                    start_time=datetime.strptime(row["Start Time"], "%Y-%m-%d %H:%M:%S"),
                    duration=_parse_duration(row["Duration"]),
                    service=self.name,
                    device=row["Device Type"] or None,
                    country=row["Country"] or None,
                )

    def billing_events(self) -> Iterator[BillingEvent]:
        # Netflix logs each charge as 1-2 rows (older exports: one SETTLED row; newer
        # exports: a duplicate NEW+APPROVED pair for the same date). Dedupe by date,
        # preferring the APPROVED row when both exist.
        path = self.export_root / "PAYMENT_AND_BILLING" / "BillingHistory.csv"
        with path.open(newline="", encoding="utf-8") as f:
            rows = [
                row
                for row in csv.DictReader(f)
                if row["Description"] == "SUBSCRIPTION" and row["Final Invoice Result"] == "SETTLED"
            ]

        by_date = {}
        for row in rows:
            date = row["Transaction Date"]
            if date not in by_date or row["Pmt Status"] == "APPROVED":
                by_date[date] = row

        for date, row in sorted(by_date.items()):
            yield BillingEvent(
                date=datetime.strptime(date, "%Y-%m-%d").date(),
                amount=float(row["Gross Sale Amt"]),
                currency=row["Currency"],
                description=row["Description"],
            )
