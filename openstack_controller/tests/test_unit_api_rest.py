# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller.api.api_rest import ApiRest
from datadog_checks.openstack_controller.api.catalog import Catalog

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
    http.get.side_effect = lambda url, params, **kwargs: MockResponse(json_data=pages[params.get('marker')])
    config = mock.MagicMock(
        paginated_limit=None, nova_microversion=None, ironic_microversion=None, cinder_microversion=None
    )
    api = ApiRest(config, mock.MagicMock(), http)

    items = api.make_paginated_request('http://service/resources', resource_name, 'id', next_signifier=next_signifier)

    assert [item['id'] for item in items] == ['a', 'b']
    assert all('limit' not in call.kwargs['params'] for call in http.get.call_args_list)


def test_paginated_request_stops_when_marker_does_not_advance():
    """A server that ignores `marker` keeps returning the same page; the check must not loop forever."""
    page = {'images': [{'id': 'a'}], 'next': '/v2/images?marker=a'}
    http = mock.MagicMock()
    http.get.side_effect = lambda url, params, **kwargs: MockResponse(json_data=page)
    config = mock.MagicMock(
        paginated_limit=None, nova_microversion=None, ironic_microversion=None, cinder_microversion=None
    )
    api = ApiRest(config, mock.MagicMock(), http)

    items = api.make_paginated_request('http://service/images', 'images', 'id', next_signifier='next')

    assert [item['id'] for item in items] == ['a']
    assert http.get.call_count == 2


COMPUTE_ROOT = 'http://127.0.0.1:8774/compute/v2.1'
BAREMETAL_ROOT = 'http://127.0.0.1:6385/baremetal'
VOLUME_ROOT = 'http://127.0.0.1:8776/volume/v3/'
CATALOG = [
    {'type': 'compute', 'endpoints': [{'interface': 'public', 'url': COMPUTE_ROOT}]},
    {'type': 'baremetal', 'endpoints': [{'interface': 'public', 'url': BAREMETAL_ROOT}]},
    {'type': 'block-storage', 'endpoints': [{'interface': 'public', 'url': VOLUME_ROOT + 'project'}]},
]


def nova_root(min_version, max_version):
    return {'version': {'id': 'v2.1', 'status': 'CURRENT', 'min_version': min_version, 'version': max_version}}


def make_api(roots, negotiate=True, **microversions):
    """`ApiRest` scoped to `project`, whose service roots answer with `roots` (a URL missing from it answers 404)."""

    def get(url, **kwargs):
        if url in roots:
            return MockResponse(json_data=roots[url])
        if url.rstrip('/') in (COMPUTE_ROOT, BAREMETAL_ROOT, VOLUME_ROOT.rstrip('/')):
            return MockResponse(status_code=404)
        return MockResponse(json_data={})

    http = mock.MagicMock()
    http.get.side_effect = get
    config = mock.MagicMock(paginated_limit=None, negotiate_microversions=negotiate)
    for service in ('nova', 'ironic', 'cinder'):
        setattr(config, f'{service}_microversion', microversions.get(service))
    api = ApiRest(config, mock.MagicMock(), http)
    api._catalog = Catalog(CATALOG, 'public', None)
    api._current_project_id = 'project'
    return api, http


def headers_sent(http, url):
    (call,) = [c for c in http.get.call_args_list if c.args[0] == url]
    return call.kwargs.get('extra_headers')


@pytest.mark.parametrize(
    ('request_resource', 'url', 'roots', 'expected'),
    [
        pytest.param(
            lambda api: api.get_compute_servers('project'),
            COMPUTE_ROOT + '/servers/detail',
            {COMPUTE_ROOT: nova_root('2.1', '2.93')},
            {'X-OpenStack-Nova-API-Version': '2.93', 'OpenStack-API-Version': 'compute 2.93'},
            id='server maximum below the openstacksdk maximum',
        ),
        pytest.param(
            lambda api: api.get_compute_server_diagnostics('server'),
            COMPUTE_ROOT + '/servers/server/diagnostics',
            {COMPUTE_ROOT: nova_root('2.1', '2.93')},
            {'X-OpenStack-Nova-API-Version': '2.48', 'OpenStack-API-Version': 'compute 2.48'},
            id='openstacksdk maximum below the server maximum',
        ),
        pytest.param(
            lambda api: api.get_compute_server_diagnostics('server'),
            COMPUTE_ROOT + '/servers/server/diagnostics',
            {COMPUTE_ROOT: nova_root('2.50', '2.93')},
            None,
            id='openstacksdk maximum below the server minimum',
        ),
        pytest.param(
            lambda api: api.get_compute_limits('project'),
            COMPUTE_ROOT + '/limits',
            {COMPUTE_ROOT: nova_root('2.1', '2.93')},
            None,
            id='resource openstacksdk requests without a microversion',
        ),
        pytest.param(
            lambda api: api.get_baremetal_conductors(),
            BAREMETAL_ROOT + '/v1/conductors',
            {BAREMETAL_ROOT: {'default_version': {'id': 'v1', 'min_version': '1.1', 'version': '1.80'}}},
            {'X-OpenStack-Ironic-API-Version': '1.49', 'OpenStack-API-Version': 'baremetal 1.49'},
            id='ironic',
        ),
        pytest.param(
            lambda api: api.get_block_storage_volumes('project'),
            VOLUME_ROOT + 'project/volumes/detail',
            {VOLUME_ROOT: {'versions': [{'id': 'v3.0', 'status': 'CURRENT', 'min_version': '3.0', 'version': '3.70'}]}},
            {'OpenStack-API-Version': 'volume 3.70'},
            id='cinder',
        ),
        pytest.param(
            lambda api: api.get_compute_servers('project'),
            COMPUTE_ROOT + '/servers/detail',
            {},
            None,
            id='version discovery fails',
        ),
        pytest.param(
            lambda api: api.get_compute_servers('project'),
            COMPUTE_ROOT + '/servers/detail',
            {COMPUTE_ROOT: nova_root('', '')},
            None,
            id='service without microversions',
        ),
        pytest.param(
            lambda api: api.get_block_storage_volumes('project'),
            VOLUME_ROOT + 'project/volumes/detail',
            {
                VOLUME_ROOT: {
                    'versions': [
                        {'id': 'v2.0', 'status': 'DEPRECATED', 'min_version': '', 'version': ''},
                        {'id': 'v3.0', 'status': 'CURRENT', 'min_version': '3.0', 'version': '3.70'},
                    ]
                }
            },
            {'OpenStack-API-Version': 'volume 3.70'},
            id='cinder current version among several',
        ),
        pytest.param(
            lambda api: api.get_compute_servers('project'),
            COMPUTE_ROOT + '/servers/detail',
            {COMPUTE_ROOT: [{'id': 'v2.1'}]},
            None,
            id='unexpected version document',
        ),
    ],
)
def test_clouds_yaml_instance_sends_openstacksdk_microversion(request_resource, url, roots, expected):
    """`openstack_config_file_path` instances used to request each resource at the microversion openstacksdk chose."""
    api, http = make_api(roots)

    request_resource(api)

    assert headers_sent(http, url) == expected


@pytest.mark.parametrize(
    ('negotiate', 'microversions'),
    [
        pytest.param(True, {'nova': '2.60'}, id='configured microversion'),
        pytest.param(False, {}, id='keystone_server_url instance'),
    ],
)
def test_microversion_not_negotiated(negotiate, microversions):
    api, http = make_api({COMPUTE_ROOT: nova_root('2.1', '2.93')}, negotiate=negotiate, **microversions)

    api.get_compute_servers('project')

    assert headers_sent(http, COMPUTE_ROOT + '/servers/detail') is None
    assert all(c.args[0] != COMPUTE_ROOT for c in http.get.call_args_list)
