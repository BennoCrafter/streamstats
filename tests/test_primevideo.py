from datetime import timedelta
from pathlib import Path

from streaming import PrimeVideoService, ViewingEvent

EXPORT_ROOT = Path(__file__).parent.parent / "sample_data" / "primevideo"


def test_viewing_events():
    events = list(PrimeVideoService(EXPORT_ROOT).viewing_events())
    # Viewing History: 6 rows, the 0-second trailer-preview row skipped -> 5.
    # Watch Events adds "Hidden Gem Special", the all-caps "NOT AVAILABLE" placeholder
    # (falls back to title "unknown"), and a rewatch of "The Grand Adventure: Season 2"
    # on a day Viewing History doesn't have; its same-day Watch Events row is deduped
    # against Viewing History, and the 0-second/"Not Available"/deleted rows are skipped.
    assert len(events) == 8
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

    # Watch Events title not present in Viewing History must be added, with no
    # profile/device/country to report
    hidden_gem = next(e for e in events if e.title == "Hidden Gem Special")
    assert hidden_gem.profile == "unknown"
    assert hidden_gem.device is None

    # same title+day covered by both sources must not be double-counted, but a
    # rewatch on a different day (only in Watch Events) must still come through
    assert sum(1 for e in events if e.title == "The Grand Adventure: Season 2") == 2

    # Amazon's all-caps "NOT AVAILABLE" placeholder must fall back to "unknown" too
    assert not any(e.title == "NOT AVAILABLE" for e in events)

    assert {e.profile for e in events} == {"ADULT", "CHILD", "unknown"}


def test_billing_events():
    # Amazon's Prime Video export has no price field - this is a real data gap, not a bug.
    events = list(PrimeVideoService(EXPORT_ROOT).billing_events())
    assert events == []


def test_billing_events_with_configured_price():
    # with no real billing data, a configured price estimates one charge per
    # month of viewing activity (across Viewing History + Watch Events combined)
    service = PrimeVideoService(EXPORT_ROOT, monthly_price=8.99, currency="EUR")
    viewing_months = {(e.start_time.year, e.start_time.month) for e in service.viewing_events()}
    events = list(service.billing_events())
    assert len(events) == len(viewing_months)
    assert all(e.amount == 8.99 and e.currency == "EUR" for e in events)
    dates = [e.date for e in events]
    assert dates == sorted(dates)


if __name__ == "__main__":
    test_viewing_events()
    test_billing_events()
    test_billing_events_with_configured_price()
    print("ok")
