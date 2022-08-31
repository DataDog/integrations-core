# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import contextlib
import logging
import os
import shutil
import tempfile
import time
import zipfile
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
_DEFAULT_PORT = 8080


class _CustomTCPServer(TCPServer):
    """A custom TCP server that reuses address."""

    allow_reuse_address = True


def _do_local_http_server(queue, directory, port):
    """Serve requests in a separate thread."""
    curr_dir = os.getcwd()
    os.chdir(directory)
    try:
        httpd = _CustomTCPServer(("", port), partial(SimpleHTTPRequestHandler))
        queue.put(httpd)
        httpd.serve_forever()
        queue.task_done()
    finally:
        os.chdir(curr_dir)


@contextlib.contextmanager
def local_http_server(test_case, port=_DEFAULT_PORT):
    """Use a zip file with tests and start a local HTTP server for E2E tests."""
    zip_file_path = os.path.join(_E2E_TESTS_DATA_DIR, test_case + ".zip")
    served_dir = tempfile.mkdtemp(prefix=test_case)

    try:
        with zipfile.ZipFile(zip_file_path) as tests_zip_file:
            tests_zip_file.extractall(path=served_dir)

        with local_http_server_local_dir(served_dir, port=port) as server_url:
            yield server_url
    finally:
        shutil.rmtree(served_dir)


@contextlib.contextmanager
def local_http_server_local_dir(local_dir, port=_DEFAULT_PORT):
    """Start a local HTTP server for E2E tests serving content from a local directory."""
    if not os.path.isdir(local_dir):
        raise Exception("directory {!r} does not exist or {!r} is not a directory".format(local_dir, local_dir))

    server_url = "http://localhost:{}".format(port)

    queue = Queue()  # Pass httpd to handle proper shutdown on exit.
    http_server_thread = Thread(target=_do_local_http_server, args=(queue, local_dir, port))
    http_server_thread.start()

    httpd = queue.get()
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
        queue.join()
        http_server_thread.join()
