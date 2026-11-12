# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import select
import socket
import threading
from collections import deque
from contextlib import closing
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from uuid import uuid4

from datadog_checks.postgres import PostgreSql


def request(check: PostgreSql, address: str, query: str = "SELECT 1 AS value", **limits: int) -> dict:
    return {
        "operation": "execute",
        "target": {"host": check._config.host, "port": check._config.port, "dbname": check._config.dbname},
        "query": query,
        "includeSchema": True,
        "resultDelivery": {
            "runId": str(uuid4()),
            "taskId": str(uuid4()),
            "uploadId": "test-upload",
            "baseUrl": address,
            "limits": {
                "maxFileBytes": 16384,
                "maxResultBytes": 1048576,
                "maxRowBytes": 16384,
                "maxColumns": 1024,
                "maxSchemaBytes": 8192,
                "maxPages": 100,
                "timeoutMs": 5000,
                **limits,
            },
        },
    }


def call(check: PostgreSql, value: dict) -> dict:
    return json.loads(check.remote_query(json.dumps(value)))


class StubIntake:
    def __init__(self) -> None:
        self.records: list[dict] = []
        self.responses: dict[str, deque] = {}
        self.observed = threading.Event()
        self.callback = None
        self.before_body = None
        self.body_reader = None
        self.retain_bodies = True
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.handle_request()

            def do_PUT(self) -> None:
                self.handle_request()

            def handle_request(self) -> None:
                if owner.before_body:
                    owner.before_body(self.path)
                length = int(self.headers.get("Content-Length", "0"))
                if owner.body_reader and "/pages/" in self.path:
                    body = owner.body_reader(self.connection, self.rfile, length)
                elif owner.retain_bodies:
                    body = self.rfile.read(length)
                else:
                    # Quality measurements must not count a second full page in the in-process stub.
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(remaining, 65536))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                    body = b""
                path = self.path.split("/uploads/test-upload", 1)[-1]
                record = {"method": self.command, "path": path, "headers": dict(self.headers), "body": body}
                owner.records.append(record if owner.retain_bodies else {**record, "body": b""})
                owner.observed.set()
                if owner.callback:
                    owner.callback(record)
                replies = owner.responses.get(path)
                status, code = replies.popleft() if replies else (204, "")
                if status == 0:
                    self.close_connection = True
                    return
                response = (
                    json.dumps({"error": {"code": code, "message": "DO NOT PROPAGATE THIS MESSAGE"}}).encode()
                    if status != 204
                    else b""
                )
                try:
                    self.send_response(status)
                    self.send_header("Content-Length", str(len(response)))
                    if status == 302:
                        self.send_header("Location", "http://127.0.0.1:1/credential-leak")
                    self.end_headers()
                    self.wfile.write(response)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, format: str, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def address(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/intake"

    def start(self) -> None:
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    @property
    def pages(self) -> list[dict]:
        return [r for r in self.records if r["path"].startswith("/pages/")]

    def reply(self, path: str, *values: tuple[int, str]) -> None:
        self.responses[path] = deque(values)


class StubProxy:
    """Real HTTP forward proxy with CONNECT support, used only by intake transport tests."""

    def __init__(self) -> None:
        self.requests: list[str] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_CONNECT(self) -> None:
                owner.requests.append(self.path)
                host, port = self.path.rsplit(":", 1)
                with socket.create_connection((host, int(port)), timeout=2) as upstream:
                    self.send_response(200)
                    self.end_headers()
                    sockets = [self.connection, upstream]
                    while True:
                        readable, _, _ = select.select(sockets, [], [], 2)
                        if not readable:
                            return
                        for source in readable:
                            data = source.recv(65536)
                            if not data:
                                return
                            destination = upstream if source is self.connection else self.connection
                            destination.sendall(data)

            def do_POST(self) -> None:
                self.forward()

            def do_PUT(self) -> None:
                self.forward()

            def forward(self) -> None:
                owner.requests.append(self.path)
                url = urlsplit(self.path)
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                with closing(HTTPConnection(url.hostname, url.port, timeout=2)) as connection:
                    connection.request(self.command, url.path, body, dict(self.headers))
                    response = connection.getresponse()
                    data = response.read()
                    self.send_response(response.status)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

            def log_message(self, format: str, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def address(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def start(self) -> None:
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
