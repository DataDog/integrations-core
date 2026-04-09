# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import mock
import pytest
import requests

from datadog_checks.dev.fs import get_here


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {'powerflex_gateway_url': 'https://localhost:443'}


def _get_url_path(url):
    parsed = urlparse(url)
    path = parsed.path + "?" + parsed.query if parsed.query else parsed.path
    return path.replace('::', '__')


@pytest.fixture
def mock_responses():
    responses_map = {}

    def load_fixtures():
        root = os.path.join(get_here(), 'fixtures', 'GET')
        for file in Path(root).rglob('*'):
            if file.is_file():
                relative = file.relative_to(root)
                path = '/' + str(relative.parent) if str(relative.parent) != '.' else '/'
                responses_map.setdefault(path, {})[file.stem] = json.loads(file.read_text())

    def get(url, file='response', **kwargs):
        return responses_map.get(_get_url_path(url), {}).get(file)

    load_fixtures()
    yield get


@pytest.fixture
def mock_http_call(mock_responses):
    def call(url, file='response', **kwargs):
        data = mock_responses(url, file=file, **kwargs)
        if data is not None:
            return data
        resp = requests.models.Response()
        resp.status_code = 404
        resp.reason = "Not Found"
        resp.url = url
        raise requests.exceptions.HTTPError(response=resp)

    yield call


@pytest.fixture
def mock_http_get(monkeypatch, mock_http_call):
    def get(url, *args, **kwargs):
        mock_json = mock.MagicMock(return_value=mock_http_call(url, **kwargs))
        return mock.MagicMock(json=mock_json, status_code=200)

    mock_get = mock.MagicMock(side_effect=get)
    monkeypatch.setattr('requests.Session.get', mock_get)
    return mock_get
