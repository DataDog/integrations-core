# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import mock
import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.http import MockResponse

from .common import COMPOSE_FILE, INSTANCE, LAB_INSTANCE, USE_FLY_LAB


@pytest.fixture(scope='session')
def dd_environment():
    if not USE_FLY_LAB:
        compose_file = COMPOSE_FILE
        conditions = [
            CheckDockerLogs(identifier='prometheus', patterns=['server running']),
            CheckDockerLogs(identifier='machines-api', patterns=['server running']),
            CheckEndpoints(INSTANCE["machines_api_endpoint"]),
            CheckEndpoints(INSTANCE["openmetrics_endpoint"]),
        ]
        with docker_run(compose_file, conditions=conditions):
            yield INSTANCE
    else:
        yield LAB_INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


def get_json_value_from_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def get_url_path(url):
    parsed_url = urlparse(url)
    return parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path


@pytest.fixture
def mock_responses():
    responses_map = {}

    def process_files(dir, response_parent):
        for file in dir.rglob('*'):
            if file.is_file() and file.stem != ".slash":
                relative_dir_path = (
                    "/"
                    + (str(file.parent.relative_to(dir)) if str(file.parent.relative_to(dir)) != "." else "")
                    + ("/" if (file.parent / ".slash").is_file() else "")
                )
                if relative_dir_path not in response_parent:
                    response_parent[relative_dir_path] = {}
                json_data = get_json_value_from_file(file)
                response_parent[relative_dir_path][file.stem] = json_data

    def process_dir(dir, response_parent):
        response_parent[dir.name] = {}
        process_files(dir, response_parent[dir.name])

    def create_responses_tree():
        root_dir_path = os.path.join(get_here(), 'fixtures', 'machines-api')
        method_subdirs = [d for d in Path(root_dir_path).iterdir() if d.is_dir() and d.name == 'GET']
        for method_subdir in method_subdirs:
            process_dir(method_subdir, responses_map)

    def method(method, url, file='response', headers=None, params=None):
        filename = file
        request_path = url
        request_path = request_path.replace('?', '/')
        if params:
            param_string = '/'.join(f'{key}={str(val)}' for key, val in params.items())
            request_path = f'{url}/{param_string}'

        response = responses_map.get(method, {}).get(request_path, {}).get(filename)
        return response

    create_responses_tree()
    yield method


@pytest.fixture
def mock_http_call(mock_responses):
    def call(method, url, file='response', headers=None, params=None):

        response = mock_responses(method, url, file=file, headers=headers, params=params)
        if response is not None:
            return response
        http_response = requests.models.Response()
        http_response.status_code = 404
        http_response.reason = "Not Found"
        http_response.url = url
        raise requests.exceptions.HTTPError(response=http_response)

    yield call


@pytest.fixture
def mock_http_get(request, monkeypatch, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.pop('http_error', {})

    def get(url, *args, **kwargs):
        method = 'GET'
        url = get_url_path(url)
        if http_error and url in http_error:
            return http_error[url]
        mock_status_code = mock.MagicMock(return_value=200)
        if "/metrics" in url:
            filepath = os.path.join(get_here(), 'fixtures', 'output.txt')
            return MockResponse(file_path=filepath)
        headers = kwargs.get('headers')
        params = kwargs.get('params')
        mock_json = mock.MagicMock(return_value=mock_http_call(method, url, headers=headers, params=params))
        return mock.MagicMock(json=mock_json, status_code=mock_status_code)

    mock_get = mock.MagicMock(side_effect=get)
    monkeypatch.setattr('requests.get', mock_get)
    return mock_get
