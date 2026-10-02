# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.harbor.common import HEALTH_URL, PROJECTS_URL, REGISTRIES_URL, SYSTEM_INFO_URL, VOLUME_INFO_URL

from .common import (
    HARBOR_COMPONENTS,
    HARBOR_VERSION,
    HEALTH_FIXTURE,
    PROJECTS_FIXTURE,
    REGISTRIES_FIXTURE,
    SYSTEM_INFO_FIXTURE,
    URL,
    VERSION_2_2,
    VOLUME_INFO_FIXTURE,
    VOLUME_INFO_PRE_2_2_FIXTURE,
)


def test_check_health(aggregator, harbor_check, harbor_api, fake_http_response):
    fake_http_response(HEALTH_URL.format(base_url=URL), json_data=HEALTH_FIXTURE)
    base_tags = ['tag1:val1', 'tag2']
    harbor_check._check_health(harbor_api, base_tags)

    components = HARBOR_COMPONENTS
    for c in components:
        aggregator.assert_service_check('harbor.status', AgentCheck.OK, tags=base_tags + ['component:{}'.format(c)])


def test_check_registries_health(aggregator, harbor_check, harbor_api, fake_http_response):
    fake_http_response(REGISTRIES_URL.format(base_url=URL), json_data=REGISTRIES_FIXTURE)
    tags = ['tag1:val1', 'tag2']
    harbor_check._check_registries_health(harbor_api, tags)
    tags.append('registry:demo')
    aggregator.assert_service_check('harbor.registry.status', AgentCheck.OK, tags=tags)


def test_check_registries_health_reraises_when_the_status_is_unknown(harbor_check, harbor_api, fake_http):
    # 401 and 403 are what mean the configured user is not an admin, the one case where skipping the
    # registry checks is right. The auth-token poll raises before the request is sent, so its error
    # carries no response and no status: nothing there says the user lacks permission.
    fake_http.register_response(
        'GET',
        REGISTRIES_URL.format(base_url=URL),
        HTTPClientStatusError('failed to fetch auth token'),
    )

    with pytest.raises(HTTPClientStatusError):
        harbor_check._check_registries_health(harbor_api, ['tag1:val1'])


def test_submit_disk_metrics_reraises_when_the_status_is_unknown(harbor_check, harbor_api, fake_http):
    # Same contract as the registries check above, on the endpoint that only an admin may read.
    fake_http.register_response(
        'GET',
        VOLUME_INFO_URL.format(base_url=URL),
        HTTPClientStatusError('failed to fetch auth token'),
    )

    with pytest.raises(HTTPClientStatusError):
        harbor_check._submit_disk_metrics(harbor_api, ['tag1:val1'])


def test_submit_project_metrics(aggregator, harbor_check, harbor_api, fake_http_response):
    fake_http_response(PROJECTS_URL.format(base_url=URL), json_data=PROJECTS_FIXTURE)
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_project_metrics(harbor_api, tags)
    aggregator.assert_metric('harbor.projects.count', 2, tags=tags)


def test_submit_disk_metrics(aggregator, harbor_check, harbor_api, fake_http_response):
    volume_info = VOLUME_INFO_PRE_2_2_FIXTURE if HARBOR_VERSION < VERSION_2_2 else VOLUME_INFO_FIXTURE
    fake_http_response(VOLUME_INFO_URL.format(base_url=URL), json_data=volume_info)
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_disk_metrics(harbor_api, tags)
    aggregator.assert_metric('harbor.disk.free', 5e5, tags=tags)
    aggregator.assert_metric('harbor.disk.total', 1e6, tags=tags)


def test_submit_read_only_status(aggregator, harbor_check, harbor_api, fake_http_response):
    fake_http_response(SYSTEM_INFO_URL.format(base_url=URL), json_data=SYSTEM_INFO_FIXTURE)
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_read_only_status(harbor_api, tags)
    aggregator.assert_metric('harbor.registry.read_only', 0, tags=tags)


def test_api__make_get_request(harbor_api, fake_http_response):
    url = f'{URL}/api/path'
    fake_http_response(url, json_data={'json': True})
    assert harbor_api._make_get_request('{base_url}/api/path') == {"json": True}

    fake_http_response(url, status_code=500)
    with pytest.raises(HTTPClientStatusError):
        harbor_api._make_get_request('{base_url}/api/path')


def test_api__make_paginated_get_request(harbor_api, fake_http_response):
    expected_result = [{'item': i} for i in range(20)]
    paginated_result = [[expected_result[i], expected_result[i + 1]] for i in range(0, len(expected_result) - 1, 2)]
    first_url = f'{URL}/api/path'
    next_url = f'{URL}/unused_url'
    for index, result in enumerate(paginated_result):
        fake_http_response(
            first_url if index == 0 else next_url,
            json_data=result,
            links={'next': {'url': 'unused_url'}} if index < len(paginated_result) - 1 else {},
        )

    assert harbor_api._make_paginated_get_request('{base_url}/api/path') == expected_result


def test_api__make_post_request(harbor_api, fake_http_response):
    url = f'{URL}/api/path'
    fake_http_response(url, method='POST', json_data={'json': True})
    assert harbor_api._make_post_request('{base_url}/api/path') == {"json": True}

    fake_http_response(url, method='POST', status_code=500)
    with pytest.raises(HTTPClientStatusError):
        harbor_api._make_post_request('{base_url}/api/path')
