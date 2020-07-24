# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.marklogic.api import MarkLogicApi


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
        self.ret = MockResponseWrapper(return_value)

    def get(self, url, params):
        # type: (str, Dict[str, str]) -> MockResponseWrapper
        self.url = url
        self.params = params
        return self.ret


def test_get_status_data():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_status_data(resource='server') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/server'
    assert http.params == {'view': 'status', 'format': 'json'}

    # TODO: when get_status_data will support it
    # assert api.get_status_data(name='myname', group='mygroup') == {'foo': 'bar'}


def test_get_requests_data():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_requests_data(resource='server', name='myname') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/requests'
    assert http.params == {'format': 'json', 'server-id': 'myname'}

    # TODO: when get_requests_data will support it
    # assert api.get_requests_data(group='mygroup') == {'foo': 'bar'}


def test_get_storage_data():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_storage_data(resource='database', name='Documents') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/forests'
    assert http.params == {'format': 'json', 'view': 'storage', 'database-id': 'Documents'}

    # TODO: when get_forests_storage_data will support it
    # assert api.get_forests_storage_data(group='groupname') == {'foo': 'bar'}


def test_get_resources():
    # type: () -> None
    cluster_query_resp = {
        'cluster-query': {
            'relations': {
                'relation-group': [
                    {
                        'typeref': 'databases',
                        'relation-count': {'units': 'quantity', 'value': 2},
                        'relation': [
                            {
                                'uriref': "/manage/v2/databases/App-Services",
                                'idref': '255818103205892753',
                                'nameref': 'App-Services',
                            },
                            {
                                'uriref': "/manage/v2/databases/Documents",
                                'idref': '5004266825873163057',
                                'nameref': 'Documents',
                            },
                        ],
                    },
                    {
                        'typeref': 'forests',
                        'relation-count': {'units': 'quantity', 'value': 2},
                        'relation': [
                            {
                                'uriref': "/manage/v2/forests/Modules",
                                'idref': '16024526243775340149',
                                'nameref': 'Modules',
                            },
                            {
                                'uriref': "/manage/v2/forests/Extensions",
                                'idref': '17254568917360711355',
                                'nameref': 'Extensions',
                            },
                        ],
                    },
                ]
            }
        }
    }
    http = MockRequestsWrapper(cluster_query_resp)
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_resources() == [
        {'id': '255818103205892753', 'type': 'databases', 'name': 'App-Services', 'uri': "/databases/App-Services"},
        {'id': '5004266825873163057', 'type': 'databases', 'name': 'Documents', 'uri': "/databases/Documents"},
        {'id': '16024526243775340149', 'type': 'forests', 'name': 'Modules', 'uri': "/forests/Modules"},
        {'id': '17254568917360711355', 'type': 'forests', 'name': 'Extensions', 'uri': "/forests/Extensions"},
    ]
    assert http.url == 'http://localhost:8000/manage/v2'
    assert http.params == {'view': 'query', 'format': 'json'}


def test_get_health():
    # type: () -> None
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_health() == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2'
    assert http.params == {'format': 'json', 'view': 'health'}
