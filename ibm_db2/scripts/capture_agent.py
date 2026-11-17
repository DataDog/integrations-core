# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Record local Agent DBM requests, or read their events without a backend. Requires the zstd CLI."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import threading
import time
import zlib
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

STREAM_PATHS = {
    'dbm-activity': '/api/v2/dbmactivity',
    'dbm-metrics': '/api/v2/dbmmetrics',
    'dbm-samples': '/api/v2/databasequery',
    'dbm-metadata': '/api/v2/dbmmetadata',
    'dbm-health': '/api/v2/dbmhealth',
}
MAX_BODY_BYTES = 32 * 1024 * 1024


def decode_events(body: bytes, encoding: str) -> list[dict]:
    if encoding == 'gzip':
        body = gzip.decompress(body)
    elif encoding == 'deflate':
        body = zlib.decompress(body)
    elif encoding == 'zstd':
        body = subprocess.run(['zstd', '-dq'], input=body, capture_output=True, check=True).stdout
    elif encoding not in ('', 'identity'):
        raise ValueError('Unsupported content encoding')
    if len(body) > MAX_BODY_BYTES:
        raise ValueError('Decoded body exceeds the capture limit')
    events = json.loads(body)
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        raise ValueError('Expected an Agent DBM batch of JSON objects')
    return events


def capture_server(output: Path, port: int = 19731) -> ThreadingHTTPServer:
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            pass

        def _respond(self, status: int, body: bytes = b'{}') -> None:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            self._respond(200, b'{"valid":true}')

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= MAX_BODY_BYTES:
                    self._respond(413)
                    return
                body = self.rfile.read(length)
                if path in STREAM_PATHS.values():
                    events = decode_events(body, self.headers.get('Content-Encoding', '').strip().lower())
                    record = {'received_at': time.time(), 'path': path, 'events': events}
                    with lock, output.open('a', encoding='utf-8') as capture:
                        capture.write(json.dumps(record) + '\n')
            except (ValueError, OSError, subprocess.SubprocessError, EOFError, zlib.error):
                self._respond(400)
                return
            self._respond(202)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def read_events(capture: Path, stream: str) -> Iterator[dict]:
    with capture.open(encoding='utf-8') as records:
        for line in records:
            if not line.endswith('\n'):
                return  # A live capture may still be appending its final record.
            record = json.loads(line)
            if record['path'] == STREAM_PATHS[stream]:
                yield from record['events']


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, help='JSONL capture file (contains submitted SQL and metadata)')
    parser.add_argument('--port', type=int, default=19731)
    parser.add_argument('--read', action='store_true', help='Print captured events as JSON lines instead of listening')
    parser.add_argument('--stream', choices=STREAM_PATHS, default='dbm-activity')
    args = parser.parse_args()
    if args.read:
        for event in read_events(args.capture, args.stream):
            print(json.dumps(event))
        return
    with capture_server(args.capture, args.port) as server:
        print(f'Recording DBM requests on http://127.0.0.1:{server.server_port} to {args.capture}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
