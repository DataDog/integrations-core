# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Upstream for the envoy-full fixture: serves the response shapes the shipped test services cannot.

- `/slow?s=N` holds the request open for N seconds (active gauges, route timeouts).
- `/status/<code>` answers with that status code (upstream and downstream 3xx/4xx/5xx).
- `/ws` answers a WebSocket upgrade with `101 Switching Protocols` (downstream 1xx).
- `/healthz` always fails, so the health-checked `panic` cluster stays in panic mode.
"""

import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip('/')
        if path.endswith('/slow'):
            time.sleep(float(parse_qs(url.query).get('s', ['1'])[0]))
            self._reply(200)
        elif '/status/' in path:
            self._reply(int(path.rsplit('/', 1)[1]))
        elif path.endswith('/ws'):
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.end_headers()
            self.close_connection = True
        elif path.endswith('/healthz'):
            self._reply(503)
        else:
            self._reply(200)

    do_POST = do_GET

    def _reply(self, code: int):
        body = b'ok\n'
        self.send_response(code)
        if 300 <= code < 400:
            self.send_header('Location', '/service/1')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # Envoy hangs up on timed-out requests by design; only report real errors.
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


if __name__ == '__main__':
    Server(('0.0.0.0', 8080), Handler).serve_forever()
