# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
import threading
from contextlib import contextmanager

from datadog_checks.base.utils.discovery.tcp import tcp_probe
from datadog_checks.base.utils.discovery.verifiers import (
    response_equals,
    response_starts_with,
)


@contextmanager
def _tcp_server(handler):
    """Run a one-shot TCP server on 127.0.0.1 and return its bound port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    done = threading.Event()

    def serve():
        try:
            conn, _ = sock.accept()
            try:
                handler(conn)
            finally:
                conn.close()
        except OSError:
            pass
        finally:
            done.set()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        sock.close()
        done.wait(timeout=1.0)


def test_tcp_probe_zookeeper_4lw_pattern():
    def handler(conn):
        data = conn.recv(64)
        if data == b"ruok":
            conn.sendall(b"imok")

    with _tcp_server(handler) as port:
        assert tcp_probe("127.0.0.1", port, send=b"ruok", verify=response_equals(b"imok"), timeout=1.0)


def test_tcp_probe_redis_ping_pattern():
    def handler(conn):
        conn.recv(64)
        conn.sendall(b"+PONG\r\n")

    with _tcp_server(handler) as port:
        assert tcp_probe("127.0.0.1", port, send=b"PING\r\n", verify=response_starts_with(b"+PONG"), timeout=1.0)


def test_tcp_probe_server_speaks_first():
    def handler(conn):
        conn.sendall(b'{"service":"nutcracker","source":"x","version":"0.5"}')

    with _tcp_server(handler) as port:
        assert tcp_probe("127.0.0.1", port, verify=response_starts_with(b'{"service":"nutcracker"'), timeout=1.0)


def test_tcp_probe_returns_false_when_verifier_rejects():
    def handler(conn):
        conn.sendall(b"WRONG")

    with _tcp_server(handler) as port:
        assert not tcp_probe("127.0.0.1", port, verify=response_starts_with(b"+PONG"), timeout=1.0)


def test_tcp_probe_returns_false_on_refused_connection():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()  # port is now free; nothing listening
    assert not tcp_probe("127.0.0.1", port, verify=response_starts_with(b"x"), timeout=1.0)


def test_tcp_probe_returns_false_on_timeout():
    def handler(conn):
        # Stall: never send anything, never close (until the test releases us).
        import time

        time.sleep(2.0)

    with _tcp_server(handler) as port:
        assert not tcp_probe("127.0.0.1", port, verify=response_starts_with(b"x"), timeout=0.1)
