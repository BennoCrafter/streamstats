from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path

from flask import Flask, abort, render_template, request

from streaming import NetflixService, PrimeVideoService, analytics

app = Flask(__name__)

# Your own Netflix/Prime Video "request your data" export goes in raw_data/ (gitignored,
# never committed). Without it, the app runs on the small synthetic sample_data/ instead.
ROOT = Path(__file__).parent / "raw_data"
if not ROOT.exists():
    ROOT = Path(__file__).parent / "sample_data"
SERVICES = {
    "netflix": NetflixService(ROOT / "netflix"),
    "primevideo": PrimeVideoService(ROOT / "primevideo"),
}

RANGE_OPTIONS = [
    ("week", "Last week", timedelta(days=7)),
    ("3m", "Last 3 months", timedelta(days=90)),
    ("6m", "Last 6 months", timedelta(days=182)),
    ("1y", "Last year", timedelta(days=365)),
    ("all", "All time", None),
]
RANGE_DELTAS = {key: delta for key, _, delta in RANGE_OPTIONS}


def _current_range():
    key = request.args.get("range", "all")
    if key not in RANGE_DELTAS:
        key = "all"
    delta = RANGE_DELTAS[key]
    return key, (datetime.now() - delta if delta else None)


def _filtered(service, cutoff):
    viewing = [e for e in service.viewing_events() if cutoff is None or e.start_time >= cutoff]
    cutoff_date = cutoff.date() if cutoff else None
    billing = [e for e in service.billing_events() if cutoff_date is None or e.date >= cutoff_date]
    return viewing, billing


@app.route("/")
def overview():
    range_key, cutoff = _current_range()

    viewing_by_service = {}
    billing_by_service = {}
    for svc in SERVICES.values():
        viewing_by_service[svc.name], billing_by_service[svc.name] = _filtered(svc, cutoff)

    all_viewing = list(chain.from_iterable(viewing_by_service.values()))
    all_billing = list(chain.from_iterable(billing_by_service.values()))

    return render_template(
        "overview.html",
        title="All services dashboard",
        services=SERVICES,
        active_key="all",
        range_key=range_key,
        range_options=RANGE_OPTIONS,
        summary=analytics.summary(all_viewing, all_billing),
        hours_per_month=analytics.hours_per_month_by_service(viewing_by_service),
        top_titles=analytics.top_titles(all_viewing),
        watched_titles=analytics.watched_titles(all_viewing),
        billed_services=sorted(name for name, events in billing_by_service.items() if events),
        unbilled_services=sorted(name for name, events in billing_by_service.items() if not events),
    )


@app.route("/<service_key>")
def dashboard(service_key):
    service = SERVICES.get(service_key)
    if service is None:
        abort(404)

    range_key, cutoff = _current_range()
    viewing, billing = _filtered(service, cutoff)

    return render_template(
        "index.html",
        title=f"{service.name} dashboard",
        services=SERVICES,
        active_key=service_key,
        range_key=range_key,
        range_options=RANGE_OPTIONS,
        service_name=service.name,
        summary=analytics.summary(viewing, billing),
        hours_per_month=analytics.hours_per_month_by_profile(viewing),
        spend_per_month=analytics.spend_per_month(billing),
        cost_per_hour=analytics.cost_per_hour_per_month(viewing, billing),
        top_titles=analytics.top_titles(viewing),
        watched_titles=analytics.watched_titles(viewing),
    )


if __name__ == "__main__":
    app.run(debug=True, port=8001)
