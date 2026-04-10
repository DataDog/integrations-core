# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev.fs import get_here

from .common import INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE


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
        root_dir_path = os.path.join(get_here(), 'fixtures')
        method_subdirs = [d for d in Path(root_dir_path).iterdir() if d.is_dir() and d.name == 'GET']
        for method_subdir in method_subdirs:
            process_dir(method_subdir, responses_map)

    def method(method, url, file='response', headers=None, params=None):
        filename = file
        request_path = url
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
        raise HTTPStatusError('404 Client Error', response=MockHTTPResponse(status_code=404, url=url))

    yield call


@pytest.fixture
def mock_http_get(request, mock_http, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.pop('http_error', {})

    def get(url, *args, **kwargs):
        method = 'GET'
        url = get_url_path(url)
        if http_error and url in http_error:
            return http_error[url]
        headers = kwargs.get('headers')
        params = kwargs.get('params')
        json_data = mock_http_call(method, url, headers=headers, params=params)
        return MockHTTPResponse(json_data=json_data)

    mock_http.get.side_effect = get
    return mock_http.get
