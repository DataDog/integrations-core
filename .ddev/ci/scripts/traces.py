# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import argparse
import json
import socket
import sys
from base64 import b64decode
from contextlib import closing
from http.client import HTTPConnection


def capture(*, record_file: str, port: int) -> None:
    """Minimal socket-based capture server"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', port))
    server_socket.listen(5)
    
    print(f"[SOCKET] Starting capture server on port {port}", file=sys.stderr)
    
    try:
        while True:
            client_socket, address = server_socket.accept()
            print(f"[SOCKET] Connection from {address}", file=sys.stderr)
            
            try:
                # Read the request
                request_data = b''
                while True:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    request_data += chunk
                    # Simple check: if we have headers and body, we're done
                    if b'\r\n\r\n' in request_data:
                        # Parse Content-Length
                        headers_end = request_data.index(b'\r\n\r\n')
                        headers = request_data[:headers_end].decode('latin-1')
                        body_start = headers_end + 4
                        
                        content_length = 0
                        for line in headers.split('\r\n'):
                            if line.lower().startswith('content-length:'):
                                content_length = int(line.split(':', 1)[1].strip())
                        
                        # Check if we have the full body
                        if len(request_data) >= body_start + content_length:
                            break
                
                # Parse request
                headers_end = request_data.index(b'\r\n\r\n')
                headers_part = request_data[:headers_end].decode('latin-1')
                body = request_data[headers_end + 4:]
                
                # Parse first line for path
                first_line = headers_part.split('\r\n')[0]
                method, path, _ = first_line.split(' ', 2)
                
                # Parse headers
                headers_dict = {}
                for line in headers_part.split('\r\n')[1:]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers_dict[key.strip()] = value.strip()
                
                # Print request details
                print(f"[SOCKET] {method} {path}", file=sys.stderr)
                print(f"[SOCKET] Headers: {headers_dict}", file=sys.stderr)
                print(f"[SOCKET] Body ({len(body)} bytes): {body[:200]}...", file=sys.stderr)
                
                # Send response
                response = b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK'
                client_socket.sendall(response)
                
            except Exception as e:
                print(f"[SOCKET] Error handling request: {e}", file=sys.stderr)
            finally:
                client_socket.close()
                
    except KeyboardInterrupt:
        print("\n[SOCKET] Shutting down", file=sys.stderr)
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
