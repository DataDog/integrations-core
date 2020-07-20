# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.marklogic.api import MarkLogicApi


class MockResponseWrapper:
    def __init__(self, return_value, status=200):
        self.ret = return_value
        self.status = status

    def raise_for_status(self):
        if self.status != 200:
            raise Exception()

    def json(self):
        return self.ret


class MockRequestsWrapper:
    def __init__(self, return_value):
        self.ret = MockResponseWrapper(return_value)

    def get(self, url, params):
        self.url = url
        self.params = params
        return self.ret


def test_get_status_data():
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_status_data(resource='server') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/forests'
    assert http.params == {'view': 'status', 'format': 'json'}

    # TODO: when get_status_data will support it
    # assert api.get_status_data(name='myname', group='mygroup') == {'foo': 'bar'}


def test_get_requests_data():
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_requests_data(resource='server', name='myname') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/requests'
    assert http.params == {'format': 'json', 'server-id': 'myname'}

    # TODO: when get_requests_data will support it
    # assert api.get_requests_data(group='mygroup') == {'foo': 'bar'}


def test_get_forests_storage_data():
    http = MockRequestsWrapper({'foo': 'bar'})
    api = MarkLogicApi(http, 'http://localhost:8000')

    assert api.get_forests_storage_data(name='forestname') == {'foo': 'bar'}
    assert http.url == 'http://localhost:8000/manage/v2/forests/forestname'
    assert http.params == {'format': 'json', 'view': 'storage'}

    # TODO: when get_forests_storage_data will support it
    # assert api.get_forests_storage_data(group='groupname') == {'foo': 'bar'}
