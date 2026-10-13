# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""An in-process PAN-OS XML API for unit tests, patched in place of `RequestsWrapper.post`.

Each firewall IP answers from a fixture set (`FIREWALL_SETS`) through `fixture_map`. Tests inject failures per host
with `FakePanos.fail()` and inspect `FakePanos.calls`, which records what was asked but never the key itself.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

import requests

from .common import FIXTURES
from .fixture_map import find_op_fixture

# Firewall IP -> fixture set.
FIREWALL_SETS = {'192.0.2.10': 'fw-a', '192.0.2.11': 'fw-b'}

# The keygen success shape (`result/key`) from the PAN-OS XML API docs ("Get Your API Key"), with a dummy key. Kept
# inline rather than in `fixtures/synthetic/`: fixture files must hold no `<key>` (see `test_fixtures_hold_no_secrets`).
KEYGEN_OK = b'<response status="success"><result><key>FAKE-KEY-0000</key></result></response>'
INVALID_CREDENTIAL = (FIXTURES / 'synthetic' / 'auth_invalid_credential.xml').read_bytes()
# Stand-in for a command the fixture set has no capture for (for example `show interface all` on fw-b): PAN-OS
# answers commands it cannot run with `status="error"`.
NO_CAPTURE = b'<response status="error" code="400"><msg><line>no capture for this command</line></msg></response>'

Answer = tuple[int, bytes] | Exception

FAILURES: dict[str, Answer] = {
    'timeout': requests.exceptions.ReadTimeout('read timed out'),
    'refused': requests.exceptions.ConnectionError('connection refused'),
    'tls': requests.exceptions.SSLError('certificate verify failed'),
    'http_403': (403, INVALID_CREDENTIAL),
    'code_403': (200, INVALID_CREDENTIAL),
    # Non-PAN-OS bodies, such as a reverse proxy's or a hung management web server's error page.
    'html_502': (502, b'<html><body><h1>502 Bad Gateway</h1></body></html>'),
    'html_403': (403, b'<html><body><h1>403 Forbidden</h1></body></html>'),
}


@dataclass(frozen=True)
class Call:
    host: str
    type: str
    cmd: str | None
    action: str | None
    key_sent: bool


class FakePanos:
    def __init__(self) -> None:
        self.calls: list[Call] = []
        self._failures: dict[tuple[str, str], Answer] = {}

    def fail(self, host: str, failure: str, on: Literal['all', 'keygen', 'api'] = 'all') -> None:
        """Answer every later request of kind `on` to `host` with the named entry of FAILURES."""
        for kind in ('keygen', 'api') if on == 'all' else (on,):
            self._failures[host, kind] = FAILURES[failure]

    def recover(self, host: str) -> None:
        self._failures = {k: v for k, v in self._failures.items() if k[0] != host}

    def calls_to(self, host: str) -> list[Call]:
        return [c for c in self.calls if c.host == host]

    def post(self, url: str, **options: Any) -> requests.Response:
        host = urlsplit(url).hostname or ''
        data: dict[str, str] = options['data']
        kind = 'keygen' if data.get('type') == 'keygen' else 'api'
        self.calls.append(
            Call(
                host=host,
                type=data.get('type', ''),
                cmd=data.get('cmd'),
                action=data.get('action'),
                key_sent='X-PAN-KEY' in (options.get('extra_headers') or {}),
            )
        )
        answer = self._failures.get((host, kind)) or self._answer(host, data)
        if isinstance(answer, Exception):
            raise answer
        return _response(url, *answer)

    def _answer(self, host: str, data: dict[str, str]) -> Answer:
        if data.get('type') == 'keygen':
            return 200, KEYGEN_OK
        if host not in FIREWALL_SETS:
            return requests.exceptions.ConnectionError(f'no fake firewall at {host}')
        path = find_op_fixture(data['cmd'], FIREWALL_SETS[host]) if data.get('type') == 'op' else None
        return (200, path.read_bytes()) if path else (200, NO_CAPTURE)


def _response(url: str, status: int, body: bytes) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp.raw = io.BytesIO(body)
    resp.url = url
    return resp
