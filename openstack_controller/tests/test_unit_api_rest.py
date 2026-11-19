# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller.api.api_rest import ApiRest

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ('resource_name', 'next_signifier', 'first_page'),
    [
        pytest.param(
            'images',
            'next',
            {'images': [{'id': 'a'}], 'next': '/v2/images?marker=a'},
            id='next key',
        ),
        pytest.param(
            'networks',
            'networks_links',
            {'networks': [{'id': 'a'}], 'networks_links': [{'rel': 'next', 'href': '/v2.0/networks?marker=a'}]},
            id='links list',
        ),
    ],
)
def test_paginated_request_without_limit_follows_next_pages(resource_name, next_signifier, first_page):
    """Without `paginated_limit`, servers still truncate long collections to their default page size."""
    pages = {None: first_page, 'a': {resource_name: [{'id': 'b'}]}}
    http = mock.MagicMock()
    http.get.side_effect = lambda url, params: MockResponse(json_data=pages[params.get('marker')])
    config = mock.MagicMock(
        paginated_limit=None, nova_microversion=None, ironic_microversion=None, cinder_microversion=None
    )
    api = ApiRest(config, mock.MagicMock(), http)

    items = api.make_paginated_request('http://service/resources', resource_name, 'id', next_signifier=next_signifier)

    assert [item['id'] for item in items] == ['a', 'b']
    assert all('limit' not in call.kwargs['params'] for call in http.get.call_args_list)
