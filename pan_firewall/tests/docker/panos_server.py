# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""A fake PAN-OS XML API over HTTPS, shared by the fake firewall and the fake Panorama containers.

It answers from `tests/fixture_map.py`, the map the unit fake (`tests/fake_panos.py`) also uses. Keygen checks the
credentials and returns a dummy key; every other call must carry that key in `X-PAN-KEY`.
"""

import re
import threading
from collections.abc import Callable
from pathlib import Path

from flask import Flask, Response, request

from tests.fake_panos import FAKE_KEY, INVALID_CREDENTIAL, KEYGEN_OK, NO_CAPTURE

CERT_FILE = '/app/certs/cert.pem'
KEY_FILE = '/app/certs/key.pem'
KEY_HEADER = 'X-PAN-KEY'

ACTIVE_JOB = b'<response status="success"><result><job><id>%s</id><status>ACT</status></job></result></response>'

OpAnswer = Callable[[str], Path | None]
JobFixtures = Callable[[dict[str, str]], tuple[Path, Path] | None]


def _xml(body: bytes, status: int = 200) -> Response:
    return Response(body, status=status, mimetype='text/xml')


def create_app(
    username: str, password: str, op_fixture: OpAnswer, log_fixtures: JobFixtures, report_fixtures: JobFixtures
) -> Flask:
    """Build the app. Each fixture callback returns the file answering a request, or None when there is no capture."""
    app = Flask(__name__)
    # A job answers `ACT` to its first `get` and its fixture from the second on, so the check's polling is exercised.
    reads: dict[tuple[str, str], int] = {}
    # The finished-job fixture by (kind, job id), set by the submit that opened the job.
    finished: dict[tuple[str, str], Path] = {}
    lock = threading.Lock()

    @app.post('/api/')
    def api() -> Response:
        data = request.form.to_dict()
        if data.get('type') == 'keygen':
            if data.get('user') == username and data.get('password') == password:
                return _xml(KEYGEN_OK)
            return _xml(INVALID_CREDENTIAL, 403)
        if request.headers.get(KEY_HEADER) != FAKE_KEY:
            return _xml(INVALID_CREDENTIAL, 403)
        kind = data.get('type', '')
        if kind == 'op':
            path = op_fixture(data.get('cmd', ''))
            return _xml(path.read_bytes() if path else NO_CAPTURE)
        if kind in ('log', 'report'):
            return _job(kind, data)
        return _xml(NO_CAPTURE)

    def _job(kind: str, data: dict[str, str]) -> Response:
        if data.get('action') == 'get':
            job_id = data.get('job-id', '')
            response = finished.get((kind, job_id))
            if response is None:
                return _xml(NO_CAPTURE)
            with lock:
                read = reads[kind, job_id] = reads.get((kind, job_id), 0) + 1
            return _xml(ACTIVE_JOB % job_id.encode() if read == 1 else response.read_bytes())
        if kind == 'report' and data.get('async') != 'yes':  # PAN-OS refuses a report submit that is not asynchronous
            return _xml(NO_CAPTURE)
        fixtures = (log_fixtures if kind == 'log' else report_fixtures)(data)
        if fixtures is None:
            return _xml(NO_CAPTURE)
        response, submit = fixtures
        submit_body = submit.read_bytes()
        match = re.search(rb'<job>(\d+)</job>', submit_body)
        if match is None:
            return _xml(NO_CAPTURE)
        job_id = match.group(1).decode()
        with lock:
            finished[kind, job_id] = response
            reads[kind, job_id] = 0
        return _xml(submit_body)

    return app


def serve(app: Flask) -> None:
    app.run(host='0.0.0.0', port=443, ssl_context=(CERT_FILE, KEY_FILE), threaded=True)
