# Architecture

How the code is structured, and what to touch when adding a service or a chart.

## Layers

```
streaming/          data access - parses each service's export into a common shape
  base.py              ViewingEvent, BillingEvent (dataclasses) + StreamingService (ABC)
  netflix.py           NetflixService(StreamingService)
  primevideo.py        PrimeVideoService(StreamingService)
  analytics.py         aggregates over ViewingEvent/BillingEvent streams - service-agnostic

app.py               Flask routes - wire a service's events through analytics into a template

templates/
  base.html             shared chrome: palette, nav tabs, range filter, table search/sort JS
  index.html            single-service dashboard (extends base.html)
  overview.html         all-services combined dashboard (extends base.html)

sample_data/         tiny synthetic exports so the app runs out of the box
raw_data/             your own real export data
```

## The superclass model

Every streaming service's data export looks different (Netflix ships CSVs with German
column headers in some locales, Amazon double-quotes its strings, neither agrees on what
a "profile" is). `streaming/base.py` defines the shape every service normalises into:

```python
@dataclass
class ViewingEvent:
    profile: str
    title: str
    start_time: datetime
    duration: timedelta
    device: str | None = None
    country: str | None = None

@dataclass
class BillingEvent:
    date: date
    amount: float
    currency: str
    description: str

class StreamingService(ABC):
    name: str
    def viewing_events(self) -> Iterator[ViewingEvent]: ...
    def billing_events(self) -> Iterator[BillingEvent]: ...
```

Everything above `streaming/netflix.py` / `streaming/primevideo.py` - the analytics
functions, the Flask routes, the templates - only ever sees `ViewingEvent` and
`BillingEvent`. None of it knows Netflix or Prime Video exist. That's what makes adding a
third service additive rather than invasive (see below).

A service with no price data (Prime Video) just yields nothing from `billing_events()` -
an empty iterator is a valid, expected answer, not an error. The dashboard checks
`summary.has_billing` and hides the spend/cost-per-hour charts when it's `False`, with a
one-line explanation instead of a misleading €0 chart.

## Parsing quirks live in the service, not in analytics

Each service's `.py` file is where format-specific mess gets absorbed:

- **Netflix** (`netflix.py`) logs each subscription charge as 1-2 CSV rows depending on
  export era (`billing_events()` dedupes by date, preferring the `APPROVED` row when both
  exist) and folds episode titles ("Show: Season 2: ... (Episode 14)") into their show
  name for aggregation.
- **Prime Video** (`primevideo.py`) wraps string fields in an extra layer of quotes
  (`"""DE"""` parses to the literal string `"DE"`) and the `_clean()` helper strips that
  and maps Amazon's `"Not available"` placeholder to `None`. Zero-second rows (autoplay
  previews) are skipped at parse time, the same way Netflix's near-zero rows are skipped
  later, in analytics (see below).

`analytics.py` never does per-service `if` branches - if you find yourself adding one
there, the fix almost always belongs in the service's parser instead.

## analytics.py

Pure functions over `Iterable[ViewingEvent]` / `Iterable[BillingEvent]`, returning plain
dicts/lists that templates can `| tojson` straight into Chart.js, or loop over directly:

| Function | Used by |
|---|---|
| `hours_per_month_by_profile` | per-service "viewing hours per month" chart |
| `hours_per_month_by_service` | overview "viewing hours per month, by service" chart |
| `spend_per_month` / `cost_per_hour_per_month` | per-service billing charts |
| `top_titles(events, n=10)` | "most-watched" bar chart |
| `watched_titles(events)` | the full, searchable/sortable "everything watched" table |
| `summary(viewing, billing)` | the stat-tile row, incl. `format_duration()` and `time_equivalents()` |

Titles whose total watch time rounds to 0.0 hours (autoplay previews, trailers) are
dropped in `top_titles` and `watched_titles` - they're real rows in the source data, but
not something a human would call "watched".

## app.py

Three routes, same shape:

- `/` - **overview**: combines every registered service's events (`chain.from_iterable`)
  and renders `overview.html`.
- `/<service_key>` - **per-service**: looks up one `StreamingService` from the `SERVICES`
  dict and renders `index.html`.
- Both read `?range=` (`week` / `3m` / `6m` / `1y` / `all`) and filter events by date
  *before* handing them to `analytics` - the filter is a cutoff on raw events, not a
  client-side chart option, so every number on the page (KPIs, charts, the watched-titles
  table) agrees for the selected window.

`SERVICES` is the registry - a dict of `key -> StreamingService` instance. Adding a
service is adding one line here plus the two files described below.

`ROOT` prefers `raw_data/` (your real, gitignored export) and falls back to
`sample_data/` (committed, synthetic) so the app runs immediately after a fresh clone.

## Templates

`base.html` owns everything shared: the CSS custom properties (light/dark palette, see
`dataviz` skill conventions - categorical hues in a fixed order, sequential blue for
single-series charts), the nav tabs, the range-filter row, and `wireTable()` - a small
vanilla-JS helper that makes any `<table>` searchable (by its first column) and sortable
(click a header) without a charting/table library.

`index.html` and `overview.html` only supply their own `content` and `script` blocks -
the chart definitions (`new Chart(...)`) and which `<canvas>`/`<table>` ids exist on that
page.

## Adding a new service

1. `streaming/<service>.py`: a `StreamingService` subclass. Implement `viewing_events()`
   and `billing_events()` (an empty generator is fine if the export has no pricing).
   Absorb that export's format quirks here (see "Parsing quirks" above).
2. Export it from `streaming/__init__.py`.
3. `app.py`: add one line to `SERVICES`.
4. `sample_data/<service>/...`: a handful of synthetic rows in that service's real export
   format, enough to exercise the parser's edge cases (a zero-duration row, a title that
   needs folding, etc.) - see the existing sample data for the pattern.
5. `test_<service>.py`: mirror `test_netflix.py` / `test_primevideo.py` against the sample
   data.

Nothing in `analytics.py` or the templates needs to change - they already operate on the
`ViewingEvent`/`BillingEvent` superclass shape.
