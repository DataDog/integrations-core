# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
from datadog_checks.marklogic.api import MarkLogicApi

pytestmark = pytest.mark.unit


def build_api(http: FakeHTTPClient, api_url: str = 'http://localhost:8000') -> MarkLogicApi:
    return MarkLogicApi(http, api_url)


def register_foo_bar(http: FakeHTTPClient, url: str) -> None:
    http.register_response('GET', url, FakeHTTPResponse(json_result={'foo': 'bar'}))


def test_url_is_correct_without_trailing_slash(fake_http):
    api = build_api(fake_http, 'http://localhost:8002')
    assert api._base_url == 'http://localhost:8002/manage/v2'


def test_url_is_correct_with_trailing_slash(fake_http):
    api = build_api(fake_http, 'http://localhost:8002/')
    assert api._base_url == 'http://localhost:8002/manage/v2'


def test_get_status_data(fake_http):
    api = build_api(fake_http)
    register_foo_bar(fake_http, 'http://localhost:8000/manage/v2/servers')
    register_foo_bar(fake_http, 'http://localhost:8000/manage/v2')

    assert api.get_status_data(resource='servers') == {'foo': 'bar'}
    assert api.get_status_data() == {'foo': 'bar'}

    fake_http.assert_requests(
        [
            RecordedRequest(
                'GET', 'http://localhost:8000/manage/v2/servers', {'params': {'view': 'status', 'format': 'json'}}
            ),
            RecordedRequest('GET', 'http://localhost:8000/manage/v2', {'params': {'view': 'status', 'format': 'json'}}),
        ]
    )


def test_get_requests_data(fake_http):
    api = build_api(fake_http)
    for _ in range(2):
        register_foo_bar(fake_http, 'http://localhost:8000/manage/v2/requests')

    assert api.get_requests_data(resource='server', name='myname') == {'foo': 'bar'}
    assert api.get_requests_data(resource='server', name='myname', group='mygroup') == {'foo': 'bar'}

    fake_http.assert_requests(
        [
            RecordedRequest(
                'GET', 'http://localhost:8000/manage/v2/requests', {'params': {'format': 'json', 'server-id': 'myname'}}
            ),
            RecordedRequest(
                'GET',
                'http://localhost:8000/manage/v2/requests',
                {'params': {'format': 'json', 'server-id': 'myname', 'group-id': 'mygroup'}},
            ),
        ]
    )


def test_get_storage_data(fake_http):
    api = build_api(fake_http)
    for _ in range(2):
        register_foo_bar(fake_http, 'http://localhost:8000/manage/v2/forests')

    assert api.get_storage_data(resource='database', name='Documents') == {'foo': 'bar'}
    assert api.get_storage_data(resource='database', name='Documents', group='groupname') == {'foo': 'bar'}

    fake_http.assert_requests(
        [
            RecordedRequest(
                'GET',
                'http://localhost:8000/manage/v2/forests',
                {'params': {'format': 'json', 'view': 'storage', 'database-id': 'Documents'}},
            ),
            RecordedRequest(
                'GET',
                'http://localhost:8000/manage/v2/forests',
                {'params': {'format': 'json', 'view': 'storage', 'database-id': 'Documents', 'group-id': 'groupname'}},
            ),
        ]
    )


def test_get_health(fake_http):
    api = build_api(fake_http)
    register_foo_bar(fake_http, 'http://localhost:8000/manage/v2')

    assert api.get_health() == {'foo': 'bar'}
    fake_http.assert_requests(
        [RecordedRequest('GET', 'http://localhost:8000/manage/v2', {'params': {'format': 'json', 'view': 'health'}})]
    )
