# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.harbor.common import REGISTRIES_URL, VOLUME_INFO_URL

from .common import HARBOR_COMPONENTS, URL


@pytest.mark.usefixtures("harbor_responses")
def test_check_health(aggregator, harbor_check, harbor_api):
    base_tags = ['tag1:val1', 'tag2']
    harbor_check._check_health(harbor_api, base_tags)

    components = HARBOR_COMPONENTS
    for c in components:
        aggregator.assert_service_check('harbor.status', AgentCheck.OK, tags=base_tags + ['component:{}'.format(c)])


@pytest.mark.usefixtures("harbor_responses")
def test_check_registries_health(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._check_registries_health(harbor_api, tags)
    tags.append('registry:demo')
    aggregator.assert_service_check('harbor.registry.status', AgentCheck.OK, tags=tags)


@pytest.mark.usefixtures("harbor_responses")
def test_submit_project_metrics(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_project_metrics(harbor_api, tags)
    aggregator.assert_metric('harbor.projects.count', 2, tags=tags)


@pytest.mark.usefixtures("harbor_responses")
def test_submit_disk_metrics(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_disk_metrics(harbor_api, tags)
    aggregator.assert_metric('harbor.disk.free', 5e5, tags=tags)
    aggregator.assert_metric('harbor.disk.total', 1e6, tags=tags)


@pytest.mark.usefixtures("harbor_responses")
def test_submit_read_only_status(aggregator, harbor_check, harbor_api):
    tags = ['tag1:val1', 'tag2']
    harbor_check._submit_read_only_status(harbor_api, tags)
    aggregator.assert_metric('harbor.registry.read_only', 0, tags=tags)


@pytest.mark.parametrize(
    'method_name, url_template, status_code',
    [
        pytest.param('_check_registries_health', REGISTRIES_URL, 401, id='registries unauthorized'),
        pytest.param('_submit_disk_metrics', VOLUME_INFO_URL, 403, id='volumes forbidden'),
    ],
)
def test_non_admin_user_skips_admin_endpoints(
    aggregator, harbor_check, harbor_api, fake_http_response, method_name, url_template, status_code
):
    # These endpoints need admin rights; a non-admin user must not fail the whole run.
    fake_http_response(url_template.format(base_url=URL), status_code=status_code)

    getattr(harbor_check, method_name)(harbor_api, [])

    aggregator.assert_service_check('harbor.registry.status', count=0)
    aggregator.assert_metric('harbor.disk.free', count=0)


def test_api__make_get_request(harbor_api, fake_http_response):
    fake_http_response(f'{URL}/api/path', json_data={'json': True})
    assert harbor_api._make_get_request('{base_url}/api/path') == {"json": True}

    fake_http_response(f'{URL}/api/path', status_code=500)
    with pytest.raises(HTTPClientStatusError):
        harbor_api._make_get_request('{base_url}/api/path')


def test_api__make_paginated_get_request(harbor_api, fake_http_response):
    expected_result = [{'item': i} for i in range(20)]
    paginated_result = [[expected_result[i], expected_result[i + 1]] for i in range(0, len(expected_result) - 1, 2)]
    # The first page comes from the requested path, every later page from the `next` link of the previous one.
    urls = [f'{URL}/api/path'] + [f'{URL}/unused_url'] * (len(paginated_result) - 1)
    for index, (url, page) in enumerate(zip(urls, paginated_result)):
        is_last = index == len(paginated_result) - 1
        fake_http_response(
            url,
            json_data=page,
            links={} if is_last else {'next': {'url': 'unused_url', 'rel': 'next', 'type': 'text/plain'}},
            once=True,
        )

    assert harbor_api._make_paginated_get_request('{base_url}/api/path') == expected_result


def test_api__make_post_request(harbor_api, fake_http_response):
    fake_http_response(f'{URL}/api/path', method='POST', json_data={'json': True})
    assert harbor_api._make_post_request('{base_url}/api/path') == {"json": True}

    fake_http_response(f'{URL}/api/path', method='POST', status_code=500)
    with pytest.raises(HTTPClientStatusError):
        harbor_api._make_post_request('{base_url}/api/path')
