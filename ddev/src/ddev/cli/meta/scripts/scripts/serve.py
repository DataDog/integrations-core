# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

FORMAT = 'prometheus'

if FORMAT == 'openmetrics':
    CONTENT_TYPE = 'application/openmetrics-text; version=0.0.1; charset=utf-8'
else:
    CONTENT_TYPE = 'plain/text; charset=utf-8'

METRICS_FILE = "/tmp/metrics{}.txt"
PORT = 8080


class OpenMetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global current_payload
        global payloads

        if len(payloads) > 1:
            print(f"Serving file {payloads[current_payload]}")

        self.send_response(200)
        self.send_header('Content-Type', CONTENT_TYPE)
        self.end_headers()
        with open(f"/tmp/{payloads[current_payload]}", 'rb') as f:
            self.wfile.write(f.read())

        # Otherwise we keep using the last one
        if current_payload < len(payloads) - 1:
            current_payload += 1


if __name__ == '__main__':
    current_payload = 0
    payloads = sys.argv[1:]
    with HTTPServer(("", PORT), OpenMetricsHandler) as httpd:
        httpd.serve_forever()
