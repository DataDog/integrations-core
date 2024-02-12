# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from http.server import BaseHTTPRequestHandler, HTTPServer

FORMAT = 'prometheus'

if FORMAT == 'openmetrics':
    CONTENT_TYPE = 'application/openmetrics-text; version=0.0.1; charset=utf-8'
else:
    CONTENT_TYPE = 'plain/text; charset=utf-8'

METRICS_FILE = "/tmp/metrics.txt"


class OpenMetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', CONTENT_TYPE)
        self.end_headers()
        with open(METRICS_FILE, 'rb') as f:
            self.wfile.write(f.read())


PORT = 8080


if __name__ == '__main__':
    with HTTPServer(("", PORT), OpenMetricsHandler) as httpd:
        httpd.serve_forever()
