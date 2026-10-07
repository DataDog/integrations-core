# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gzip
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

VALID_PAYLOAD = b'# TYPE my_metric gauge\nmy_metric{foo="bar"} 42\n'


def make_large_payload(size):
    """A body of `size` bytes that does not contain any newline."""
    return b'x' * size


@contextmanager
def serve_payload(body, compress=True):
    """Serve `body` on a local port for the duration of the context, yielding the URL."""
    wire_body = gzip.compress(body) if compress else body

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            if compress:
                self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(wire_body)))
            self.end_headers()
            try:
                self.wfile.write(wire_body)
            except (BrokenPipeError, ConnectionResetError):
                # The client may stop reading once the size limit is exceeded
                pass

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:{}/metrics'.format(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
