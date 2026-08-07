# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from mock import MagicMock

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.dev.http import MockHTTPResponse

from .common import HARBOR_COMPONENTS


@pytest.mark.usefixtures("patch_requests")
def test_check_health(aggregator, harbor_check, harbor_api):
    base_tags = ['tag1:val1', 'tag2']
    harbor_check._check_health(harbor_api, base_tags)

    components = HARBOR_COMPONENTS
    for c in components:
        aggregator.assert_service_check('harbor.status', AgentCheck.OK, tags=base_tags + ['component:{}'.format(c)])


@pytest.mark.usefixtures("patch_requests")
def test_check_registries_health(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._check_registries_health(harbor_api, tags)
    tags.append('registry:demo')
    aggregator.assert_service_check('harbor.registry.status', AgentCheck.OK, tags=tags)


@pytest.mark.usefixtures("patch_requests")
def test_check_registries_health_reraises_when_the_status_is_unknown(harbor_check, harbor_api):
    # 401 and 403 are what mean the configured user is not an admin, the one case where skipping the
    # registry checks is right. The auth-token poll raises before the request is sent, so its error
    # carries no response and no status: nothing there says the user lacks permission.
    harbor_api.http.get.side_effect = HTTPStatusError('failed to fetch auth token')

    with pytest.raises(HTTPStatusError):
        harbor_check._check_registries_health(harbor_api, ['tag1:val1'])


@pytest.mark.usefixtures("patch_requests")
def test_submit_disk_metrics_reraises_when_the_status_is_unknown(harbor_check, harbor_api):
    # Same contract as the registries check above, on the endpoint that only an admin may read.
    harbor_api.http.get.side_effect = HTTPStatusError('failed to fetch auth token')

    with pytest.raises(HTTPStatusError):
        harbor_check._submit_disk_metrics(harbor_api, ['tag1:val1'])


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
def test_submit_read_only_status(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_read_only_status(harbor_api, tags)
    aggregator.assert_metric('harbor.registry.read_only', 0, tags=tags)


def test_api__make_get_request(harbor_api):
    harbor_api.http = MagicMock()
    harbor_api.http.get = MagicMock(return_value=MockHTTPResponse(json_data={'json': True}))
    assert harbor_api._make_get_request('{base_url}/api/path') == {"json": True}

    harbor_api.http.get = MagicMock(return_value=MockHTTPResponse(status_code=500))
    with pytest.raises(HTTPStatusError):
        harbor_api._make_get_request('{base_url}/api/path')


def test_api__make_paginated_get_request(harbor_api):
    expected_result = [{'item': i} for i in range(20)]
    paginated_result = [[expected_result[i], expected_result[i + 1]] for i in range(0, len(expected_result) - 1, 2)]
    values = []
    for r in paginated_result:
        values.append(
            MockHTTPResponse(json_data=r, headers={'link': 'Link: <unused_url>; rel=next; type="text/plain"'})
        )
    values[-1].headers.pop('link')

    harbor_api.http = MagicMock()
    harbor_api.http.get = MagicMock(side_effect=values)

    assert harbor_api._make_paginated_get_request('{base_url}/api/path') == expected_result


def test_api__make_post_request(harbor_api):
    harbor_api.http = MagicMock()
    harbor_api.http.post = MagicMock(return_value=MockHTTPResponse(json_data={'json': True}))
    assert harbor_api._make_post_request('{base_url}/api/path') == {"json": True}

    harbor_api.http.post = MagicMock(return_value=MockHTTPResponse(status_code=500))
    with pytest.raises(HTTPStatusError):
        harbor_api._make_post_request('{base_url}/api/path')
