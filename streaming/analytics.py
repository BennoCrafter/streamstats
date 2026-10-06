"""Aggregates over normalised ViewingEvent/BillingEvent streams.

Works for any service built on the StreamingService superclass, not just Netflix.
"""

import re
from collections import defaultdict
from typing import Iterable, Optional, Tuple

from .base import BillingEvent, ViewingEvent
from .primevideo import PrimeVideoService


def _month_key(d) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def hours_per_month_by_profile(events: Iterable[ViewingEvent]) -> dict:
    """{"months": [...], "series": {profile: [hours_per_month, ...]}}"""
    totals = defaultdict(lambda: defaultdict(float))
    for e in events:
        totals[_month_key(e.start_time)][e.profile] += e.duration.total_seconds() / 3600

    months = sorted(totals)
    profiles = sorted({p for month in totals.values() for p in month})
    series = {p: [round(totals[m].get(p, 0.0), 2) for m in months] for p in profiles}
    return {"months": months, "series": series}


def hours_per_month_by_service(events_by_service: dict) -> dict:
    """{"months": [...], "series": {service_name: [hours_per_month, ...]}}"""
    totals = defaultdict(lambda: defaultdict(float))
    for service, events in events_by_service.items():
        for e in events:
            totals[_month_key(e.start_time)][service] += e.duration.total_seconds() / 3600

    months = sorted(totals)
    services = sorted(events_by_service)
    series = {s: [round(totals[m].get(s, 0.0), 2) for m in months] for s in services}
    return {"months": months, "series": series}


def titles_by_month(events: Iterable[ViewingEvent]) -> dict:
    """{month_key: [{"title", "date", "hours", "service"}, ...]}, each month's list date-sorted."""
    by_month = defaultdict(list)
    for e in events:
        show, season = _show_name_and_season(e)
        by_month[_month_key(e.start_time)].append(
            {
                "title": _display_title(show, {season} if season is not None else set()),
                "date": e.start_time.date().isoformat(),
                "hours": round(e.duration.total_seconds() / 3600, 2),
                "service": e.service,
            }
        )
    for rows in by_month.values():
        rows.sort(key=lambda r: r["date"])
    return by_month


def spend_per_month(events: Iterable[BillingEvent]) -> dict:
    """{"months": [...], "amounts": [...]}"""
    totals = defaultdict(float)
    for e in events:
        totals[_month_key(e.date)] += e.amount

    months = sorted(totals)
    return {"months": months, "amounts": [round(totals[m], 2) for m in months]}


def cost_per_hour_per_month(viewing_events: Iterable[ViewingEvent], billing_events: Iterable[BillingEvent]) -> dict:
    """{"months": [...], "cost_per_hour": [...]}  (only months with both hours and spend)"""
    hours = defaultdict(float)
    for e in viewing_events:
        hours[_month_key(e.start_time)] += e.duration.total_seconds() / 3600

    spend = defaultdict(float)
    for e in billing_events:
        spend[_month_key(e.date)] += e.amount

    months = sorted(set(hours) & set(spend))
    return {
        "months": months,
        "cost_per_hour": [round(spend[m] / hours[m], 2) if hours[m] else None for m in months],
    }


# Prime Video joins TV episodes as "<episode>-<series> - Season N" (unspaced dash
# only between episode and series) - a quirk specific to Prime's export, so only
# stripped for Prime's own events below. "Season N"/"Staffel N" after a "-"/":"
# separator is common to both services (e.g. Netflix's "Show: Season 2: Episode"),
# so that part applies generically; its lazy match skips over an incidental unspaced
# dash inside the show's own name (e.g. "Brooklyn Nine-Nine") since nothing with
# "Season"/"Staffel" immediately follows it.
_EPISODE_PREFIX = re.compile(r"^.+[^ ]-([^ ].*)$")
_SEASON_SUFFIX = re.compile(r"^(.*?)\s*[-–:]\s*(?:Season|Staffel)\s*(\d+)\b.*$", re.IGNORECASE)


def _show_name_and_season(event: ViewingEvent) -> Tuple[str, Optional[int]]:
    """ "Pilot-Reacher - Season 2" -> ("Reacher", 2); "Show: Season 2: Ep" -> ("Show", 2)."""
    title = event.title
    rest = title
    if event.service == PrimeVideoService.name:
        match = _EPISODE_PREFIX.match(title)
        rest = match.group(1) if match else title

    match = _SEASON_SUFFIX.match(rest)
    if match:
        return match.group(1).strip() or rest, int(match.group(2))

    return rest.split(":")[0].strip() or rest, None


def _display_title(show: str, seasons: set) -> str:
    """Combine every season watched into one row: "Show" + {1, 2} -> "Show (Season 1, 2)"."""
    if not seasons:
        return show
    return f"{show} (Season {', '.join(str(s) for s in sorted(seasons))})"


def top_titles(events: Iterable[ViewingEvent], n: int = 10) -> list:
    """[(show_title, hours), ...] sorted descending, episodes/seasons folded into their show."""
    hours = defaultdict(float)
    seasons = defaultdict(set)
    for e in events:
        show, season = _show_name_and_season(e)
        hours[show] += e.duration.total_seconds() / 3600
        if season is not None:
            seasons[show].add(season)

    ranked = sorted(hours.items(), key=lambda kv: kv[1], reverse=True)
    ranked = [(_display_title(show, seasons[show]), round(h, 1)) for show, h in ranked if round(h, 1) > 0]
    return ranked[:n]


def watched_titles(events: Iterable[ViewingEvent]) -> list:
    """Every show watched, most recently watched first, seasons folded into one row.

    [{"title", "hours", "sessions", "last_watched"}, ...]
    """
    agg = defaultdict(lambda: {"hours": 0.0, "sessions": 0, "last_watched": None, "seasons": set()})
    for e in events:
        show, season = _show_name_and_season(e)
        row = agg[show]
        row["hours"] += e.duration.total_seconds() / 3600
        row["sessions"] += 1
        if season is not None:
            row["seasons"].add(season)
        if row["last_watched"] is None or e.start_time > row["last_watched"]:
            row["last_watched"] = e.start_time

    rows = [
        {
            "title": _display_title(show, row["seasons"]),
            "hours": round(row["hours"], 1),
            "sessions": row["sessions"],
            "last_watched": row["last_watched"].date().isoformat(),
        }
        for show, row in agg.items()
        if round(row["hours"], 1) > 0
    ]
    rows.sort(key=lambda r: r["last_watched"], reverse=True)
    return rows


def format_duration(total_hours: float) -> str:
    """2916.2 -> "121 days, 12 hours" (adds a years part once it's that long)."""
    years, rem_days = divmod(total_hours / 24, 365.25)
    days, rem_hours = divmod(rem_days, 1)
    hours = round(rem_hours * 24)
    years, days = int(years), int(days)

    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if days or years:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    return ", ".join(parts)


# label, hours per unit - a personal-growth ladder: real, widely-cited milestones,
# ordered so each rung is a bigger "what you could have become" than the last
_TIME_EQUIVALENTS = [
    ("FAA private pilot licenses earned, minimum required flight hours (~40h each)", 40),
    ("musical instruments learned to a basic playing level (~250h each)", 250),
    ("marathons trained for and run, from first base-building run (~400h each)", 400),
    ("new languages learned to conversational fluency (~700h each)", 700),
    ("bachelor's degrees worth of class and study time (~1,800h each)", 1800),
    ('skills mastered, the "10,000-hour rule" (~10,000h each)', 10000),
]


def time_equivalents(total_hours: float) -> list:
    """[(label, count), ...] - what else that many hours could have bought you."""
    return [(label, round(total_hours / per_unit, 1)) for label, per_unit in _TIME_EQUIVALENTS]


CINEMA_COST_PER_HOUR = 5.5


def summary(viewing_events: Iterable[ViewingEvent], billing_events: Iterable[BillingEvent]) -> dict:
    """Headline totals for the stat-tile row."""
    viewing_events = list(viewing_events)
    billing_events = list(billing_events)

    total_hours = sum(e.duration.total_seconds() for e in viewing_events) / 3600
    total_spent = sum(e.amount for e in billing_events)
    currency = billing_events[0].currency if billing_events else ""
    cost_per_hour = round(total_spent / total_hours, 2) if total_hours and billing_events else None

    return {
        "total_hours": round(total_hours, 1),
        "duration_text": format_duration(total_hours),
        "time_equivalents": time_equivalents(total_hours),
        "has_billing": bool(billing_events),
        "total_spent": round(total_spent, 2),
        "currency": currency,
        "cost_per_hour": cost_per_hour,
        "months_billed": len({_month_key(e.date) for e in billing_events}),
        "cinema_cost_per_hour": CINEMA_COST_PER_HOUR,
        "cheaper_than_cinema": cost_per_hour is not None and cost_per_hour < CINEMA_COST_PER_HOUR,
    }
