# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import argparse
import json
import socket
from base64 import b64decode
from contextlib import closing
from http.client import HTTPConnection


def capture(*, record_file: str, port: int) -> None:
    """Minimal socket-based server that just returns 200 OK"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('127.0.0.1', port))
    server_socket.listen(1)
    
    try:
        while True:
            client_socket, _ = server_socket.accept()
            try:
                # Single recv to avoid hanging on reading
                client_socket.recv(4096)
                # Send 200 OK response
                client_socket.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK')
            finally:
                client_socket.close()
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()


def replay(*, record_file: str, port: int) -> None:
    with closing(HTTPConnection('localhost', port)) as conn, open(record_file, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            path = record['path']
            body = b64decode(record['body'])
            conn.request('PUT', path, body=body, headers=record['headers'])
            response = conn.getresponse()
            response.read()  # Needs to be done to prevent ResponseNotReady.
            print(response.status, response.reason)


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    subparsers = parser.add_subparsers()

    for name, command in (('capture', capture), ('replay', replay)):
        subparser = subparsers.add_parser(name)
        subparser.add_argument('--record-file', required=True)
        subparser.add_argument('--port', type=int, default=8126)
        subparser.set_defaults(func=command)

    kwargs = vars(parser.parse_args())
    try:
        command = kwargs.pop('func')
    except KeyError:
        parser.print_help()
    else:
        command(**kwargs)


if __name__ == '__main__':
    main()
