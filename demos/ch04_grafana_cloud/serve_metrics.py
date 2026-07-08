"""Serve chapter 4 Prometheus text metrics for a local Prometheus scrape."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DEFAULT_METRICS_PATH = Path("artifacts/metrics/chapter_04_anomaly.prom")


class MetricsHandler(BaseHTTPRequestHandler):
    metrics_path = DEFAULT_METRICS_PATH

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found\n")
            return

        payload = self.metrics_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve artifacts/metrics/chapter_04_anomaly.prom at /metrics.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9108)
    parser.add_argument(
        "--metrics-file",
        type=Path,
        default=DEFAULT_METRICS_PATH,
        help="Prometheus text artifact path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    MetricsHandler.metrics_path = args.metrics_file
    server = HTTPServer((args.host, args.port), MetricsHandler)
    print(f"metrics_url=http://{args.host}:{args.port}/metrics")
    print(f"metrics_file={args.metrics_file}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("metrics_server_stopped=True")


if __name__ == "__main__":
    main()
