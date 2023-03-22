# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

import pytest

from datadog_checks.marklogic.api import MarkLogicApi

pytestmark = pytest.mark.unit


class MockResponseWrapper:
    def __init__(self, return_value):
        # type: (Dict[str, Any]) -> None
        self.ret = return_value

    def raise_for_status(self):
        # type: () -> None
        pass

    def json(self):
        # type: () -> Dict[str, Any]
        return self.ret


class MockRequestsWrapper:
    def __init__(self, return_value):
        # type: (Dict[str, Any]) -> None
        self.ret = MockResponseWrapper(return_value)

    def get(self, url, params):
        # type: (str, Dict[str, str]) -> MockResponseWrapper
        self.url = url
        self.params = params
        return self.ret


def test_url_is_correct_without_trailing_slash():
    # type: () -> None
    api = MarkLogicApi(MockRequestsWrapper({'foo': 'bar'}), 'http://localhost:8002')
    assert api._base_url == 'http://localhost:8002/manage/v2'


def test_url_is_correct_with_trailing_slash():
    # type: () -> None
    api = MarkLogicApi(MockRequestsWrapper({'foo': 'bar'}), 'http://localhost:8002/')
    assert api._base_url == 'http://localhost:8002/manage/v2'


def test_get_status_data():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_status_data(resource='servers') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/servers'
    assert http.params == {'view': 'status', 'format': 'json'}

    assert api.get_status_data() == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2'
    assert http.params == {'view': 'status', 'format': 'json'}


def test_get_requests_data():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_requests_data(resource='server', name='myname') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/requests'
    assert http.params == {'format': 'json', 'server-id': 'myname'}

    assert api.get_requests_data(resource='server', name='myname', group='mygroup') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/requests'
    assert http.params == {'format': 'json', 'server-id': 'myname', 'group-id': 'mygroup'}


def test_get_storage_data():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_storage_data(resource='database', name='Documents') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/forests'
    assert http.params == {'format': 'json', 'view': 'storage', 'database-id': 'Documents'}

    assert api.get_storage_data(resource='database', name='Documents', group='groupname') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/forests'
    assert http.params == {'format': 'json', 'view': 'storage', 'database-id': 'Documents', 'group-id': 'groupname'}


def test_get_health():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_health() == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2'
    assert http.params == {'format': 'json', 'view': 'health'}
