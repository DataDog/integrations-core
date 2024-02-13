# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import functools
import socketserver
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

FORMAT = 'prometheus'

if FORMAT == 'openmetrics':
    CONTENT_TYPE = 'application/openmetrics-text; version=0.0.1; charset=utf-8'
else:
    CONTENT_TYPE = 'plain/text; charset=utf-8'

PORT = 8080

current_payload = 0


class OpenMetricsHandler(BaseHTTPRequestHandler):
    def __init__(
        self, payloads, request: bytes, client_address: tuple[str, int], server: socketserver.BaseServer
    ) -> None:
        self.payloads = payloads
        super().__init__(request, client_address, server)  # type: ignore

    def do_GET(self):
        global current_payload
        if len(self.payloads) > 1:
            print(f"Serving file {self.payloads[current_payload]}")

        self.send_response(200)
        self.send_header('Content-Type', CONTENT_TYPE)
        self.end_headers()
        with open(f"/tmp/{self.payloads[current_payload]}", 'rb') as f:
            self.wfile.write(f.read())

        # Otherwise we keep using the last one
        if current_payload < len(self.payloads) - 1:
            current_payload += 1


if __name__ == '__main__':
    with HTTPServer(("", PORT), functools.partial(OpenMetricsHandler, sys.argv[1:])) as httpd:
        httpd.serve_forever()
