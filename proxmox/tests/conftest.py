# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse

from .common import INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE


FIXTURES_ROOT = Path(__file__).parent / 'fixtures' / 'GET'
SERVER = 'http://localhost:8006'


def load_fixture_responses():
    """Return `(path, params, data)` per fixture, where trailing `key=value` directories hold the query params."""
    responses = []
    for file in sorted(FIXTURES_ROOT.rglob('*.json')):
        segments = file.parent.relative_to(FIXTURES_ROOT).parts
        path_segments = [segment for segment in segments if '=' not in segment]
        params = dict(segment.split('=', 1) for segment in segments if '=' in segment)
        params = {key: int(value) if value.isdigit() else value for key, value in params.items()}
        responses.append(('/' + '/'.join(path_segments), params or None, json.loads(file.read_text())))
    return responses


@pytest.fixture
def mock_http_get(request, fake_http):
    """Register one check run worth of fixture responses and return a function that registers another.

    The optional `http_error` parameter maps a URL path to the response that replaces its fixture.
    """
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error', {})

    def register_run():
        for path, params, data in load_fixture_responses():
            if path in http_error:
                continue
            match_options = {'params': params} if params else None
            response = FakeHTTPResponse(content=json.dumps(data).encode(), json_result=data)
            fake_http.register_response('GET', SERVER + path, response, match_options=match_options)
        for path, response in http_error.items():
            fake_http.register_response('GET', SERVER + path, response)

    register_run()
    return register_run
