# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from mock import MagicMock
from requests import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse

from .common import HARBOR_COMPONENTS, HARBOR_VERSION, VERSION_1_5, VERSION_1_6, VERSION_1_8


@pytest.mark.usefixtures("patch_requests")
def test_check_health(aggregator, harbor_check, harbor_api):
    base_tags = ['tag1:val1', 'tag2']
    harbor_check._check_health(harbor_api, base_tags)

    if harbor_api.harbor_version >= VERSION_1_8:
        components = HARBOR_COMPONENTS
        for c in components:
            aggregator.assert_service_check('harbor.status', AgentCheck.OK, tags=base_tags + ['component:{}'.format(c)])
    elif harbor_api.harbor_version >= VERSION_1_6:
        aggregator.assert_service_check('harbor.status', AgentCheck.OK, tags=base_tags + ['component:chartmuseum'])
        aggregator.assert_service_check('harbor.status', AgentCheck.OK, tags=base_tags)
    elif harbor_api.harbor_version >= VERSION_1_5:
        aggregator.assert_service_check('harbor.status', AgentCheck.OK, tags=base_tags)
    else:
        aggregator.assert_service_check('harbor.status', AgentCheck.UNKNOWN, tags=base_tags)


@pytest.mark.usefixtures("patch_requests")
def test_check_registries_health(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._check_registries_health(harbor_api, tags)
    tags.append('registry:demo')
    aggregator.assert_service_check('harbor.registry.status', AgentCheck.OK, tags=tags)


@pytest.mark.usefixtures("patch_requests")
def test_submit_project_metrics(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_project_metrics(harbor_api, tags)
    aggregator.assert_metric('harbor.projects.count', 2, tags=tags)


@pytest.mark.usefixtures("patch_requests")
def test_submit_disk_metrics(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_disk_metrics(harbor_api, tags)
    aggregator.assert_metric('harbor.disk.free', 5e5, tags=tags)
    aggregator.assert_metric('harbor.disk.total', 1e6, tags=tags)


@pytest.mark.usefixtures("patch_requests")
@pytest.mark.skipif(HARBOR_VERSION < VERSION_1_5, reason="The registry.read_only metric is submitted for Harbor 1.5+")
def test_submit_read_only_status(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_read_only_status(harbor_api, tags)
    aggregator.assert_metric('harbor.registry.read_only', 0, tags=tags)


def test_api__make_get_request(harbor_api):
    harbor_api.http = MagicMock()
    harbor_api.http.get = MagicMock(return_value=MockResponse(json_data={'json': True}))
    assert harbor_api._make_get_request('{base_url}/api/path') == {"json": True}

    harbor_api.http.get = MagicMock(return_value=MockResponse(status_code=500))
    with pytest.raises(HTTPError):
        harbor_api._make_get_request('{base_url}/api/path')


def test_api__make_paginated_get_request(harbor_api):
    expected_result = [{'item': i} for i in range(20)]
    paginated_result = [[expected_result[i], expected_result[i + 1]] for i in range(0, len(expected_result) - 1, 2)]
    values = []
    for r in paginated_result:
        values.append(MockResponse(json_data=r, headers={'link': 'Link: <unused_url>; rel=next; type="text/plain"'}))
    values[-1].headers.pop('link')

    harbor_api.http = MagicMock()
    harbor_api.http.get = MagicMock(side_effect=values)

    assert harbor_api._make_paginated_get_request('{base_url}/api/path') == expected_result


def test_api__make_post_request(harbor_api):
    harbor_api.http = MagicMock()
    harbor_api.http.post = MagicMock(return_value=MockResponse(json_data={'json': True}))
    assert harbor_api._make_post_request('{base_url}/api/path') == {"json": True}

    harbor_api.http.post = MagicMock(return_value=MockResponse(status_code=500))
    with pytest.raises(HTTPError):
        harbor_api._make_post_request('{base_url}/api/path')
