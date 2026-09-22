# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import pytest

from datadog_checks.dev.http import MockHTTPResponse
from datadog_checks.marklogic.api import MarkLogicApi

pytestmark = pytest.mark.unit


def build_api(http: Any, api_url: str = 'http://localhost:8000') -> MarkLogicApi:
    http.get.return_value = MockHTTPResponse(json_data={'foo': 'bar'})
    return MarkLogicApi(http, api_url)


def test_url_is_correct_without_trailing_slash(mock_http):
    # type: (Any) -> None
    api = build_api(mock_http, 'http://localhost:8002')
    assert api._base_url == 'http://localhost:8002/manage/v2'


def test_url_is_correct_with_trailing_slash(mock_http):
    # type: (Any) -> None
    api = build_api(mock_http, 'http://localhost:8002/')
    assert api._base_url == 'http://localhost:8002/manage/v2'


def test_get_status_data(mock_http):
    # type: (Any) -> None
    api = build_api(mock_http)

    assert api.get_status_data(resource='servers') == {'foo': 'bar'}
    mock_http.get.assert_called_with(
        'http://localhost:8000/manage/v2/servers', params={'view': 'status', 'format': 'json'}
    )

    assert api.get_status_data() == {'foo': 'bar'}
    mock_http.get.assert_called_with('http://localhost:8000/manage/v2', params={'view': 'status', 'format': 'json'})


def test_get_requests_data(mock_http):
    # type: (Any) -> None
    api = build_api(mock_http)

    assert api.get_requests_data(resource='server', name='myname') == {'foo': 'bar'}
    mock_http.get.assert_called_with(
        'http://localhost:8000/manage/v2/requests', params={'format': 'json', 'server-id': 'myname'}
    )

    assert api.get_requests_data(resource='server', name='myname', group='mygroup') == {'foo': 'bar'}
    mock_http.get.assert_called_with(
        'http://localhost:8000/manage/v2/requests',
        params={'format': 'json', 'server-id': 'myname', 'group-id': 'mygroup'},
    )


def test_get_storage_data(mock_http):
    # type: (Any) -> None
    api = build_api(mock_http)

    assert api.get_storage_data(resource='database', name='Documents') == {'foo': 'bar'}
    mock_http.get.assert_called_with(
        'http://localhost:8000/manage/v2/forests',
        params={'format': 'json', 'view': 'storage', 'database-id': 'Documents'},
    )

    assert api.get_storage_data(resource='database', name='Documents', group='groupname') == {'foo': 'bar'}
    mock_http.get.assert_called_with(
        'http://localhost:8000/manage/v2/forests',
        params={'format': 'json', 'view': 'storage', 'database-id': 'Documents', 'group-id': 'groupname'},
    )


def test_get_health(mock_http):
    # type: (Any) -> None
    api = build_api(mock_http)

    assert api.get_health() == {'foo': 'bar'}
    mock_http.get.assert_called_with('http://localhost:8000/manage/v2', params={'format': 'json', 'view': 'health'})
