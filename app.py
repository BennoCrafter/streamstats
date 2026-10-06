from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import chain
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from jinja2 import Environment, FileSystemLoader

from streaming import NetflixService, PrimeVideoService, analytics

ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
env = Environment(loader=FileSystemLoader(ROOT / "templates"))
env.filters["pluralize"] = lambda items, suffix="s": suffix if len(items) != 1 else ""


DATA_ROOT = ROOT / "raw_data"
if not DATA_ROOT.exists():
    DATA_ROOT = ROOT / "sample_data"

SERVICES = {
    "netflix": NetflixService(DATA_ROOT / "netflix"),
    "primevideo": PrimeVideoService(DATA_ROOT / "primevideo"),
}

RANGE_OPTIONS = [
    ("week", "Last week", timedelta(days=7)),
    ("3m", "Last 3 months", timedelta(days=90)),
    ("6m", "Last 6 months", timedelta(days=182)),
    ("1y", "Last year", timedelta(days=365)),
    ("all", "All time", None),
]

RANGE_DELTAS = {key: delta for key, _, delta in RANGE_OPTIONS}


def _current_range(query):
    key = query.get("range", ["all"])[0]
    if key not in RANGE_DELTAS:
        key = "all"
    delta = RANGE_DELTAS[key]
    return key, (datetime.now() - delta if delta else None)


def _filtered(service, cutoff):
    viewing = [
        e for e in service.viewing_events() if cutoff is None or e.start_time >= cutoff
    ]
    cutoff_date = cutoff.date() if cutoff else None
    billing = [
        e
        for e in service.billing_events()
        if cutoff_date is None or e.date >= cutoff_date
    ]
    return viewing, billing


def render_overview(query):
    range_key, cutoff = _current_range(query)

    viewing_by_service = {}
    billing_by_service = {}
    for svc in SERVICES.values():
        viewing_by_service[svc.name], billing_by_service[svc.name] = _filtered(
            svc, cutoff
        )

    all_viewing = list(chain.from_iterable(viewing_by_service.values()))
    all_billing = list(chain.from_iterable(billing_by_service.values()))

    return env.get_template("overview.html").render(
        title="All services dashboard",
        services=SERVICES,
        active_key="all",
        range_key=range_key,
        range_options=RANGE_OPTIONS,
        summary=analytics.summary(all_viewing, all_billing),
        hours_per_month=analytics.hours_per_month_by_service(viewing_by_service),
        top_titles=analytics.top_titles(all_viewing),
        watched_titles=analytics.watched_titles(all_viewing),
        billed_services=sorted(
            name for name, events in billing_by_service.items() if events
        ),
        unbilled_services=sorted(
            name for name, events in billing_by_service.items() if not events
        ),
    )


def render_dashboard(service_key, query):
    service = SERVICES.get(service_key)
    if service is None:
        return None

    range_key, cutoff = _current_range(query)
    viewing, billing = _filtered(service, cutoff)

    return env.get_template("index.html").render(
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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = urlsplit(self.path)
        query = parse_qs(parts.query)

        if parts.path.startswith("/static/"):
            self._serve_static(parts.path.removeprefix("/static/"))
        elif parts.path == "/":
            self._respond_html(render_overview(query))
        else:
            html = render_dashboard(parts.path.strip("/"), query)
            if html is None:
                self._respond(404, b"Not found", "text/plain")
            else:
                self._respond_html(html)

    def _serve_static(self, rel_path):
        file_path = (STATIC_DIR / rel_path).resolve()
        if (
            not file_path.is_relative_to(STATIC_DIR.resolve())
            or not file_path.is_file()
        ):
            self._respond(404, b"Not found", "text/plain")
            return
        content_type, _ = guess_type(str(file_path))
        self._respond(
            200, file_path.read_bytes(), content_type or "application/octet-stream"
        )

    def _respond_html(self, html):
        self._respond(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = 8001
    print(f"Serving on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
