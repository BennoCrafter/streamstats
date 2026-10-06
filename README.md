# streamstats

A local dashboard for your own streaming-service data: how many hours you've watched,
what it cost, and what else you could have done with that time. Runs entirely on your
machine against the official "download your data" export from Netflix and Prime Video -
nothing is sent anywhere.

## Quickstart

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py
```

Open `http://127.0.0.1:8001`. Without any setup it runs on the small synthetic data in
`sample_data/` so you can see what it does immediately.

## Using your own data

1. Request your data export:
   - Netflix: account settings -> "Get my data"
   - Prime Video: Amazon "Request My Data" -> "Prime Video" (or "Your Orders and Shopping
     History" account data request)
2. Unzip it into `raw_data/netflix/` and `raw_data/primevideo/`, keeping the folder
   structure the export arrives in (e.g. `raw_data/netflix/CONTENT_INTERACTION/ViewingActivity.csv`).
3. Restart the app - it prefers `raw_data/` over `sample_data/` automatically.

`raw_data/` is gitignored; your personal data never gets committed.

## What's on the dashboard

- **Per-service** (`/netflix`, `/primevideo`): hours watched per month (by profile),
  spend per month, cost per hour watched, most-watched shows, and a searchable/sortable
  table of everything you've watched.
- **All services** (`/`): the same, combined across every service you've added.
- A time-range filter (last week / 3 months / 6 months / year / all time) scopes every
  number on the page.
- A "what else you could have done with that time" conversion (feature films, marathons,
  nights of sleep, work weeks, learning a language) next to the raw hour count.

Prime Video's export has no per-service price - Amazon bills Prime at the account level -
so its spend charts are replaced with a one-line note instead of a misleading €0.

## Code structure

See [ARCHITECTURE.md](ARCHITECTURE.md) - the short version: every service implements a
common `StreamingService` interface (`streaming/base.py`), so `streaming/analytics.py`
and the templates never know which service they're looking at. Adding a third service
is additive, not a rewrite.

## Tests

```bash
./venv/bin/python test_netflix.py
./venv/bin/python test_primevideo.py
```

Self-contained checks against `sample_data/` - no real data required.

## License

MIT, see [LICENSE](LICENSE).
