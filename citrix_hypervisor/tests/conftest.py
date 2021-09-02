# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev.http import MockResponse

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return common.MOCKED_INSTANCE


def mock_requests_get(url, *args, **kwargs):
    url_parts = url.split('/')

    if url_parts[0] != 'mocked':
        return MockResponse(status_code=404)

    extension = 'json' if kwargs['params'].get('json') else 'xml'
    path = os.path.join(common.HERE, 'fixtures', '{}.{}'.format(url_parts[1], extension))
    if not os.path.exists(path):
        return MockResponse(status_code=404)

    return MockResponse(file_path=path)


@pytest.fixture
def mock_responses():
    with mock.patch('requests.get', side_effect=mock_requests_get):
        yield
