# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from unittest import mock

import pytest

from datadog_checks.base.utils.tagging import tagger
from datadog_checks.kata_containers import KataContainersCheck


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {}


@pytest.fixture(autouse=True)
def reset_tagger():
    tagger.reset()
    yield
    tagger.reset()


@pytest.fixture
def aggregator():
    from datadog_checks.base.stubs import aggregator as _stub

    _stub.reset()
    yield _stub
    _stub.reset()


@pytest.fixture
def dd_run_check():
    def _run(check, extract_value_error=False, cancel=True):
        error = check.run()
        if error:
            raise Exception(error)
        if cancel:
            check.cancel()

    return _run


@pytest.fixture
def mock_http_response():
    """Patch RequestsWrapper.get so the OpenMetrics scraper never creates a real session.

    Patching at this level avoids the requests_unixsocket dependency while still
    exercising the full metric-parsing and service-check logic.
    """
    import requests.models

    patcher = None

    def _setup(file_path=None, status_code=200):
        nonlocal patcher

        response = requests.models.Response()
        response.status_code = status_code
        response.headers['Content-Type'] = 'text/plain; version=0.0.4; charset=utf-8'
        response.encoding = 'utf-8'
        response._content = Path(file_path).read_bytes() if file_path is not None else b''
        # Mark content as already consumed so iter_lines/iter_content use _content
        # instead of trying to read from response.raw (which is None in this mock).
        response._content_consumed = True

        patcher = mock.patch(
            'datadog_checks.base.utils.http.RequestsWrapper.get',
            return_value=response,
        )
        patcher.start()

    yield _setup

    if patcher is not None:
        patcher.stop()


@pytest.fixture
def make_check():
    """Factory fixture — call with an optional instance config dict to create a check."""

    def _factory(instance_config=None):
        return KataContainersCheck('kata_containers', {}, [instance_config or {}])

    return _factory


@pytest.fixture
def make_sandbox_mocks():
    """Factory fixture — returns OS-level mock functions for a single sandbox."""

    def _factory(sandbox_id, storage_path='/run/vc/sbs'):
        socket_path = f'{storage_path}/{sandbox_id}/shim-monitor.sock'

        def mock_exists(path):
            return path in [storage_path, socket_path]

        def mock_listdir(path):
            return [sandbox_id] if path == storage_path else []

        def mock_isdir(path):
            return path == f'{storage_path}/{sandbox_id}'

        return mock_exists, mock_listdir, mock_isdir, socket_path

    return _factory
