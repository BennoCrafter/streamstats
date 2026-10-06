from datetime import timedelta
from pathlib import Path

from streaming import BillingEvent, NetflixService, ViewingEvent

EXPORT_ROOT = Path(__file__).parent / "sample_data" / "netflix"


def test_viewing_events():
    events = list(NetflixService(EXPORT_ROOT).viewing_events())
    assert len(events) == 10
    first = events[0]
    assert isinstance(first, ViewingEvent)
    assert isinstance(first.duration, timedelta)
    assert first.title

    # a near-zero autoplay row still parses (filtering it out of reports is analytics' job)
    assert any(e.duration.total_seconds() <= 2 for e in events)
    # a title with no text before its first colon falls back to the full raw title
    assert any(e.title == ": Season 1: Clip (Clip 1)" for e in events)


def test_billing_events():
    events = list(NetflixService(EXPORT_ROOT).billing_events())
    assert [e.amount for e in events] == [9.99, 9.99, 12.99, 12.99]
    assert all(isinstance(e, BillingEvent) for e in events)
    # sample mixes the old single-row style (Jan) and the new NEW+APPROVED duplicate-row
    # style (Feb/Mar/Oct) plus a non-SUBSCRIPTION noise row - dedupe must leave exactly one per month
    dates = [e.date for e in events]
    assert len(dates) == len(set(dates)) == 4


if __name__ == "__main__":
    test_viewing_events()
    test_billing_events()
    print("ok")
