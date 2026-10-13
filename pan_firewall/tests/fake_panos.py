# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""An in-process PAN-OS XML API for unit tests, patched in place of `RequestsWrapper.post`.

Each firewall IP answers from a fixture set (`FIREWALL_SETS`) through `fixture_map`. Tests inject failures per host
with `FakePanos.fail()`, replace the answer to one command with `FakePanos.answer_op()`, and inspect
`FakePanos.calls`, which records what was asked but never the key itself.
"""

from __future__ import annotations

import io
import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import requests

from .common import FIXTURES
from .fixture_map import PANORAMA_OP_FIXTURES, find_log_fixture, find_op_fixture, find_report_fixture

# Firewall IP -> fixture set.
FIREWALL_SETS = {'192.0.2.10': 'fw-a', '192.0.2.11': 'fw-b'}

# Hosts answering as a Panorama: keygen and the commands of PANORAMA_OP_FIXTURES.
PANORAMA_HOSTS = {'panorama.example.com'}

# The keygen success shape (`result/key`) from the PAN-OS XML API docs ("Get Your API Key"), with a dummy key. Kept
# inline rather than in `fixtures/synthetic/`: fixture files must hold no `<key>` (see `test_fixtures_hold_no_secrets`).
FAKE_KEY = 'FAKE-KEY-0000'
KEYGEN_OK = f'<response status="success"><result><key>{FAKE_KEY}</key></result></response>'.encode()
INVALID_CREDENTIAL = (FIXTURES / 'synthetic' / 'auth_invalid_credential.xml').read_bytes()
# Stand-in for a command the fixture set has no capture for (for example `show interface all` on fw-b): PAN-OS
# answers commands it cannot run with `status="error"`.
NO_CAPTURE = b'<response status="error" code="400"><msg><line>no capture for this command</line></msg></response>'

SUBMIT_TEMPLATE = (
    b'<response status="success" code="19"><result><msg><line>query job enqueued with jobid %s</line></msg>'
    b'<job>%s</job></result></response>'
)
Answer = tuple[int, bytes] | Exception
LogBody = bytes | Path | Answer

FAILURES: dict[str, Answer] = {
    'timeout': requests.exceptions.ReadTimeout('read timed out'),
    'refused': requests.exceptions.ConnectionError('connection refused'),
    'tls': requests.exceptions.SSLError('certificate verify failed'),
    'http_403': (403, INVALID_CREDENTIAL),
    'code_403': (200, INVALID_CREDENTIAL),
    # The real Panorama answer to a keygen with a wrong password (lab task P1).
    'capture_bad_password': (200, (FIXTURES / 'panorama' / 'keygen_bad_password.xml').read_bytes()),
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
    params: dict[str, str] = field(default_factory=dict)


class FakePanos:
    def __init__(self) -> None:
        self.calls: list[Call] = []
        self._failures: dict[tuple[str, str], Answer] = {}
        self._op_answers: dict[tuple[str, str], Answer] = {}
        # `type=log` jobs: the bodies a `get` of the job answers in turn (the last one repeats), by (host, job id).
        self._log_overrides: dict[tuple[str, str, str | None, int], list[LogBody]] = {}
        self._log_jobs: dict[tuple[str, str], list[LogBody]] = {}
        self._log_reads: dict[tuple[str, str], int] = {}
        self._job_ids = itertools.count(9000)
        # `type=report` jobs, like the log ones: overrides by (host, aggregate-by field), bodies by (host, job id).
        self._report_overrides: dict[tuple[str, str], list[LogBody]] = {}
        self._report_jobs: dict[tuple[str, str], list[LogBody]] = {}
        self._report_reads: dict[tuple[str, str], int] = {}

    def fail(self, host: str, failure: str, on: Literal['all', 'keygen', 'api'] = 'all') -> None:
        """Answer every later request of kind `on` to `host` with the named entry of FAILURES."""
        for kind in ('keygen', 'api') if on == 'all' else (on,):
            self._failures[host, kind] = FAILURES[failure]

    def answer_op(self, host: str, cmd: str, answer: Answer) -> None:
        """Answer every later `type=op&cmd=<cmd>` request to `host` with `answer`; `fail()` still takes precedence."""
        self._op_answers[host, cmd] = answer

    def answer_log(self, host: str, direction: str, query: str | None, skip: int, *bodies: LogBody) -> None:
        """Answer `type=log` submits of (`dir`, `query`, `skip`) to `host` with a new job whose `get`s answer `bodies`.

        The bodies are served one per `get` (`get_job` or `open_log_job`), the last one repeating, so a job can
        be `ACT` for a while and then finish. A body is bytes, a fixture path, or an `Answer` (a failure).
        """
        self._log_overrides[host, direction, query, skip] = list(bodies)

    def answer_report(self, host: str, field: str, *bodies: LogBody) -> None:
        """Answer report submits aggregated by `field` to `host` with a new job whose `get`s answer `bodies` in turn."""
        self._report_overrides[host, field] = list(bodies)

    def recover(self, host: str) -> None:
        self._failures = {k: v for k, v in self._failures.items() if k[0] != host}
        self._op_answers = {k: v for k, v in self._op_answers.items() if k[0] != host}
        self._log_overrides = {k: v for k, v in self._log_overrides.items() if k[0] != host}
        self._report_overrides = {k: v for k, v in self._report_overrides.items() if k[0] != host}

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
                params=dict(data),
            )
        )
        answer = (
            self._failures.get((host, kind))
            or (data.get('type') == 'op' and self._op_answers.get((host, data.get('cmd', ''))))
            or (data.get('type') == 'log' and self._answer_log(host, data))
            or (data.get('type') == 'report' and self._answer_report(host, data))
            or self._answer(host, data)
        )
        if isinstance(answer, Exception):
            raise answer
        return _response(url, *answer)

    def _answer(self, host: str, data: dict[str, str]) -> Answer:
        if data.get('type') == 'keygen':
            return 200, KEYGEN_OK
        if host in PANORAMA_HOSTS:
            fixture = PANORAMA_OP_FIXTURES.get(data.get('cmd', ''))
            return (200, (FIXTURES / fixture).read_bytes()) if fixture else (200, NO_CAPTURE)
        if host not in FIREWALL_SETS:
            return requests.exceptions.ConnectionError(f'no fake firewall at {host}')
        path = find_op_fixture(data['cmd'], FIREWALL_SETS[host]) if data.get('type') == 'op' else None
        return (200, path.read_bytes()) if path else (200, NO_CAPTURE)

    def _answer_log(self, host: str, data: dict[str, str]) -> Answer | None:
        """Answer a `type=log` submit or `action=get`; None for anything else, which `_answer` then handles."""
        if host not in FIREWALL_SETS:
            return None
        if data.get('action') == 'get':
            return self._read_log_job(host, data.get('job-id', ''))
        direction, query, skip = data.get('dir', ''), data.get('query'), int(data.get('skip', '0'))
        return self._open_job(
            self._log_jobs,
            self._log_reads,
            host,
            self._log_overrides.get((host, direction, query, skip)),
            find_log_fixture(direction, query, skip, FIREWALL_SETS[host]),
        )

    def _answer_report(self, host: str, data: dict[str, str]) -> Answer | None:
        """Answer a `type=report` submit or `action=get`; None for an unknown host, which `_answer` then handles."""
        if host not in FIREWALL_SETS:
            return None
        if data.get('action') == 'get':
            return self._read_job(self._report_jobs, self._report_reads, host, data.get('job-id', ''))
        if data.get('async') != 'yes':  # PAN-OS refuses a report submit that is not asynchronous
            return 200, NO_CAPTURE
        match = re.search(r'<aggregate-by><member>([^<]+)</member>', data.get('cmd', ''))
        field = match.group(1) if match else ''
        return self._open_job(
            self._report_jobs,
            self._report_reads,
            host,
            self._report_overrides.get((host, field)),
            find_report_fixture(field, FIREWALL_SETS[host]),
        )

    def _open_job(
        self,
        jobs: dict[tuple[str, str], list[LogBody]],
        reads: dict[tuple[str, str], int],
        host: str,
        override: list[LogBody] | None,
        fixture: tuple[Path, Path] | None,
    ) -> Answer:
        """Register a job in `jobs` and return its submit answer: a new job answering the `override` bodies in turn, or
        the job of the (response, submit) `fixture` pair; `NO_CAPTURE` when there is neither."""
        if override is not None:
            bodies = override
            job_id = str(next(self._job_ids))
            submit = SUBMIT_TEMPLATE % (job_id.encode(), job_id.encode())
        elif fixture is not None:
            response, submit_path = fixture
            bodies = [response]
            submit = submit_path.read_bytes()
            job_id = re.search(rb'<job>(\d+)</job>', submit).group(1).decode()  # type: ignore[union-attr]
        else:
            return 200, NO_CAPTURE
        jobs[host, job_id] = bodies
        reads[host, job_id] = 0
        return 200, submit

    def _read_log_job(self, host: str, job_id: str) -> Answer:
        return self._read_job(self._log_jobs, self._log_reads, host, job_id)

    @staticmethod
    def _read_job(
        jobs: dict[tuple[str, str], list[LogBody]], reads: dict[tuple[str, str], int], host: str, job_id: str
    ) -> Answer:
        bodies = jobs.get((host, job_id))
        if bodies is None:
            return 200, NO_CAPTURE
        index = reads[host, job_id]
        reads[host, job_id] = index + 1
        body = bodies[min(index, len(bodies) - 1)]
        if isinstance(body, Path):
            return 200, body.read_bytes()
        return (200, body) if isinstance(body, bytes) else body


def _response(url: str, status: int, body: bytes) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp.raw = io.BytesIO(body)
    resp.url = url
    return resp
