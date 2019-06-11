# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from mock import MagicMock, call
from requests import HTTPError

from datadog_checks.base import AgentCheck

from .common import HARBOR_COMPONENTS, VERSION_1_5, VERSION_1_6, VERSION_1_8
from .conftest import MockResponse


@pytest.mark.usefixture("patch_requests")
def test_check_health(harbor_check, harbor_api):
    base_tags = ['tag1:val1', 'tag2']
    harbor_check._check_health(harbor_api, base_tags)
    calls = []

    if harbor_api.harbor_version >= VERSION_1_8:
        components = HARBOR_COMPONENTS
        for c in components:
            calls.append(call('harbor.status', AgentCheck.OK, tags=base_tags + ['component:{}'.format(c)]))
    elif harbor_api.harbor_version >= VERSION_1_6:
        calls.append(call('harbor.status', AgentCheck.OK, tags=base_tags + ['component:chartmuseum']))
        calls.append(call('harbor.status', AgentCheck.OK, tags=base_tags))
    elif harbor_api.harbor_version >= VERSION_1_5:
        calls.append(call('harbor.status', AgentCheck.OK, tags=base_tags))
    else:
        calls.append(call('harbor.status', AgentCheck.UNKNOWN, tags=base_tags))

    harbor_check.service_check.assert_has_calls(calls, any_order=True)
    assert harbor_check.service_check.call_count == len(calls)


@pytest.mark.usefixture("patch_requests")
def test_check_registries_health(harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._check_registries_health(harbor_api, tags)
    tags.append('registry:demo')
    harbor_check.service_check.assert_called_once_with('harbor.registry.status', AgentCheck.OK, tags=tags)


@pytest.mark.usefixture("patch_requests")
def test_submit_project_metrics(harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_project_metrics(harbor_api, tags)
    calls = [call('harbor.projects.count', 2, tags=tags)]
    harbor_check.gauge.assert_has_calls(calls, any_order=True)
    assert harbor_check.gauge.call_count == len(calls)


@pytest.mark.usefixture("patch_requests")
def test_submit_disk_metrics(harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_disk_metrics(harbor_api, tags)
    calls = [call('harbor.disk.free', 5e5, tags=tags), call('harbor.disk.total', 1e6, tags=tags)]
    harbor_check.gauge.assert_has_calls(calls, any_order=True)
    assert harbor_check.gauge.call_count == len(calls)


def test_api__make_get_request(harbor_api):
    harbor_api.http = MagicMock()
    harbor_api.http.get = MagicMock(return_value=MockResponse({"json": True}, 200))
    assert harbor_api._make_get_request('{base_url}/api/path') == {"json": True}

    harbor_api.http.get = MagicMock(return_value=MockResponse(None, 500))
    with pytest.raises(HTTPError):
        harbor_api._make_get_request('{base_url}/api/path')


def test_api__make_paginated_get_request(harbor_api):
    expected_result = [{'item': i} for i in range(20)]
    paginated_result = [[expected_result[i], expected_result[i + 1]] for i in range(0, len(expected_result) - 1, 2)]
    values = []
    for r in paginated_result:
        resp = MockResponse(r, 200)
        resp.links = {'next': {'url': 'unused_url'}}
        values.append(resp)
    values[-1].links = {}

    harbor_api.http = MagicMock()
    harbor_api.http.get = MagicMock(side_effect=values)

    assert harbor_api._make_paginated_get_request('{base_url}/api/path') == expected_result


def test_api__make_post_request(harbor_api):
    harbor_api.http = MagicMock()
    harbor_api.http.post = MagicMock(return_value=MockResponse({"json": True}, 200))
    assert harbor_api._make_post_request('{base_url}/api/path') == {"json": True}

    harbor_api.http.post = MagicMock(return_value=MockResponse(None, 500))
    with pytest.raises(HTTPError):
        harbor_api._make_post_request('{base_url}/api/path')
