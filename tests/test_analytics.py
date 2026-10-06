from datetime import datetime, timedelta

from streaming import analytics
from streaming.base import ViewingEvent


def _event(title, hours, day, service="Prime Video"):
    return ViewingEvent(
        profile="ADULT",
        title=title,
        start_time=datetime(2024, 1, day),
        duration=timedelta(hours=hours),
        service=service,
    )


def test_seasons_combine_into_one_row():
    events = [
        _event("Pilot-Reacher - Season 1", 1, 1),
        _event("Reacher - Season 2", 2, 2),
        _event("Cartoon Fun", 1, 3),
    ]

    rows = analytics.watched_titles(events)
    titles = {r["title"] for r in rows}
    assert "Reacher (Season 1, 2)" in titles
    assert "Cartoon Fun" in titles
    reacher = next(r for r in rows if r["title"] == "Reacher (Season 1, 2)")
    assert reacher["hours"] == 3.0
    assert reacher["sessions"] == 2

    top = analytics.top_titles(events)
    assert ("Reacher (Season 1, 2)", 3.0) in top


def test_en_dash_seasons_combine_too():
    # Amazon's real export writes some season suffixes with an en dash ("–") instead
    # of a hyphen ("-") - those must still fold into the same show, not a new one.
    events = [
        _event("Cherry-The Boys - Season 1", 1, 1),
        _event("What I Know-The Boys – Season 2", 1, 2),
    ]
    rows = analytics.watched_titles(events)
    assert len(rows) == 1
    assert rows[0]["title"] == "The Boys (Season 1, 2)"


def test_episode_prefix_split_is_prime_only():
    # Netflix titles don't use Prime's "<episode>-<series>" join - a Netflix title
    # with an incidental unspaced dash and no season info must pass through whole.
    events = [_event("Spider-Man: Homecoming", 1, 1, service="Netflix")]
    rows = analytics.watched_titles(events)
    assert len(rows) == 1
    assert rows[0]["title"] == "Spider-Man"


def test_netflix_seasons_combine_too():
    events = [
        _event("Brooklyn Nine-Nine: Season 1 - CLM 11", 1, 1, service="Netflix"),
        _event("Brooklyn Nine-Nine: Staffel 2: Det. Dave Majors (Folge 21)", 1, 2, service="Netflix"),
    ]
    rows = analytics.watched_titles(events)
    assert len(rows) == 1
    assert rows[0]["title"] == "Brooklyn Nine-Nine (Season 1, 2)"


if __name__ == "__main__":
    test_seasons_combine_into_one_row()
    test_en_dash_seasons_combine_too()
    test_episode_prefix_split_is_prime_only()
    test_netflix_seasons_combine_too()
    print("ok")
