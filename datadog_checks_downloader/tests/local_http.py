# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import contextlib
import logging
import os
import time
from functools import partial
from threading import Thread

import requests
import six

if six.PY3:
    from http.server import SimpleHTTPRequestHandler
    from queue import Queue
    from socketserver import TCPServer
else:
    from Queue import Queue
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from SocketServer import TCPServer

_LOGGER = logging.getLogger(__name__)
_E2E_TESTS_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_DEFAULT_PORT = int(os.getenv("DATADOG_CHECKS_DOWNLOADER_E2E_TEST_HTTP_PORT", 8080))


class _CustomTCPServer(TCPServer):
    """A custom TCP server that reuses address."""

    allow_reuse_address = True


def _do_local_http_server(q, directory, port):
    """Serve requests in a separate thread."""
    curr_dir = os.getcwd()
    os.chdir(directory)
    try:
        httpd = _CustomTCPServer(("", port), partial(SimpleHTTPRequestHandler))
        q.put(httpd)
        httpd.serve_forever()
        q.task_done()
    finally:
        os.chdir(curr_dir)


@contextlib.contextmanager
def local_http_server(distribution_dir_name, port=_DEFAULT_PORT):
    """Start a local HTTP server for E2E tests."""
    directory = os.path.join(_E2E_TESTS_DATA_DIR, distribution_dir_name)
    server_url = "http://localhost:{}".format(port)

    if not os.path.isdir(directory):
        raise RuntimeError("Cannot start HTTP server: {!r} does not exist".format(directory))

    q = Queue()  # Pass httpd to handle proper shutdown on exit.
    http_server_thread = Thread(target=_do_local_http_server, args=(q, directory, port))
    http_server_thread.start()

    httpd = q.get()
    try:
        for _ in range(5):  # Provide some time to have the HTTP server ready.
            response = requests.head(server_url)
            if response.status_code != 200:
                _LOGGER.warning(
                    "HTTP server not ready yet (HTTP status code %d)...",
                    response.status_code,
                )
                time.sleep(1)
                continue

            break
        else:
            raise RuntimeError("Failed to start HTTP server")

        yield server_url
    finally:
        httpd.shutdown()
        q.join()
        http_server_thread.join()
