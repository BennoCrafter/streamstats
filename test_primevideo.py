from datetime import timedelta
from pathlib import Path

from streaming import PrimeVideoService, ViewingEvent

EXPORT_ROOT = Path(__file__).parent / "sample_data" / "primevideo"


def test_viewing_events():
    events = list(PrimeVideoService(EXPORT_ROOT).viewing_events())
    # the sample has 6 rows; the 0-second trailer-preview row must be skipped
    assert len(events) == 5
    first = events[0]
    assert isinstance(first, ViewingEvent)
    assert isinstance(first.duration, timedelta)
    assert first.duration.total_seconds() > 0
    assert first.title
    assert '"' not in first.title  # Amazon's double-quoting must be stripped

    # Amazon's "Not available" placeholder must become None, not the literal string
    weekend_movie = next(e for e in events if e.title == "Weekend Movie")
    assert weekend_movie.country is None
    assert weekend_movie.device is None

    assert {e.profile for e in events} == {"ADULT", "CHILD"}


def test_billing_events():
    # Amazon's Prime Video export has no price field - this is a real data gap, not a bug.
    events = list(PrimeVideoService(EXPORT_ROOT).billing_events())
    assert events == []


if __name__ == "__main__":
    test_viewing_events()
    test_billing_events()
    print("ok")
