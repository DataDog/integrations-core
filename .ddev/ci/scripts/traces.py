# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import argparse
import json
from base64 import b64decode, b64encode
from contextlib import closing
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer


def capture(*, record_file: str, port: int) -> None:
    class RequestHandler(BaseHTTPRequestHandler):
        def do_PUT(self):
            content_length = int(self.headers['Content-Length'])
            body = b64encode(self.rfile.read(content_length)).decode('ascii')

            record = json.dumps(
                {'path': self.path, 'body': body, 'headers': dict(self.headers.items())}, separators=(',', ':')
            )
            with open(record_file, 'a', encoding='utf-8') as f:
                f.write(f'{record}\n')

            self.log_request(200, content_length)
            self.send_response_only(200)
            self.send_header('Server', self.version_string())
            self.send_header('Date', self.date_time_string())
            self.end_headers()
            self.wfile.write(b'OK')

    httpd = HTTPServer(('', port), RequestHandler)
    httpd.serve_forever()


def replay(*, record_file: str, port: int) -> None:
    with closing(HTTPConnection('localhost', port)) as conn, open(record_file, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            path = record['path']
            body = b64decode(record['body'])

            print(f'PUT {path} {len(body)} bytes: ', end='')
            conn.request('PUT', path, body=body, headers=record['headers'])
            print(conn.getresponse().read().decode('utf-8'))


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
