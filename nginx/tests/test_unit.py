# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
from copy import deepcopy

import mock
import pytest

from datadog_checks.nginx import Nginx

from .common import CHECK_NAME, FIXTURES_PATH, HOST, PORT, TAGS
from .utils import mocked_perform_request

pytestmark = [pytest.mark.unit]


def test_flatten_json(check, instance):
    check = check(instance)
    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_in.json')) as f:
        parsed = check.parse_json(f.read())
        parsed.sort()

    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_out.python')) as f:
        expected = eval(f.read())

    # Check that the parsed test data is the same as the expected output
    assert parsed == expected


def test_flatten_json_timestamp(check, instance):
    check = check(instance)
    assert (
        check.parse_json(
            """
    {"timestamp": "2018-10-23T12:12:23.123212Z"}
    """
        )
        == [('nginx.timestamp', 1540296743, [], 'gauge')]
    )


def test_nest_payload(check, instance):
    check = check(instance)
    keys = ["foo", "bar"]
    payload = {"key1": "val1", "key2": "val2"}

    result = check._nest_payload(keys, payload)
    expected = {"foo": {"bar": payload}}

    assert result == expected


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "legacy auth config",
            {'user': 'legacy_foo', 'password': 'legacy_bar'},
            {'auth': ('legacy_foo', 'legacy_bar')},
        ),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'ssl_validation': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_validation': False}, {'verify': False}),
    ],
)
def test_config(check, instance, test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(instance)
    instance.update(extra_config)

    c = check(instance)

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200, content=b'{}')

        c.check(instance)

        http_wargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_wargs.update(expected_http_kwargs)

        r.get.assert_called_with('http://localhost:8080/nginx_status', **http_wargs)


def test_no_version(check, instance, caplog):
    c = check(instance)

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200, content=b'{}', headers={'server': 'nginx'})

        c.check(instance)

    errors = [record for record in caplog.records if record.levelname == "ERROR"]
    assert not errors


def test_emit_generic_and_non_generic_tags_by_default(instance):
    instance = deepcopy(instance)
    instance['disable_generic_tags'] = False
    check = Nginx(CHECK_NAME, {}, [instance])
    extra_tags = ['host:localhost']
    tags = TAGS + extra_tags
    normalised_tags = TAGS + ['nginx_host:localhost', 'host:localhost']
    assert set(normalised_tags) == set(check._normalize_tags_type(tags))


def test_emit_non_generic_tags_when_disabled(instance):
    instance = deepcopy(instance)
    instance['disable_generic_tags'] = True
    check = Nginx(CHECK_NAME, {}, [instance])
    extra_tags = ['host:localhost']
    tags = TAGS + extra_tags
    normalised_tags = TAGS + ['nginx_host:localhost']
    assert set(normalised_tags) == set(check._normalize_tags_type(tags))


@pytest.mark.parametrize(
    'version, use_stream, expected_endpoints',
    [
        (
            7,
            True,
            [
                ('http/requests', ['requests']),
                ('processes', ['processes']),
                ('http/server_zones', ['server_zones']),
                ('http/upstreams', ['upstreams']),
                ('http/limit_conns', ['limit_conns']),
                ('http/location_zones', ['location_zones']),
                ('http/limit_reqs', ['limit_reqs']),
                ('nginx', []),
                ('ssl', ['ssl']),
                ('http/caches', ['caches']),
                ('connections', ['connections']),
                ('resolvers', ['resolvers']),
                ('slabs', ['slabs']),
                ('stream/limit_conns', ['stream', 'limit_conns']),
                ('stream/server_zones', ['stream', 'server_zones']),
                ('stream/zone_sync', ['stream', 'zone_sync']),
                ('stream/upstreams', ['stream', 'upstreams']),
            ],
        ),
        (
            7,
            False,
            [
                ('http/requests', ['requests']),
                ('processes', ['processes']),
                ('http/server_zones', ['server_zones']),
                ('http/upstreams', ['upstreams']),
                ('http/limit_conns', ['limit_conns']),
                ('http/location_zones', ['location_zones']),
                ('http/limit_reqs', ['limit_reqs']),
                ('nginx', []),
                ('ssl', ['ssl']),
                ('http/caches', ['caches']),
                ('connections', ['connections']),
                ('resolvers', ['resolvers']),
                ('slabs', ['slabs']),
            ],
        ),
        (
            2,
            False,
            [
                ('http/requests', ['requests']),
                ('processes', ['processes']),
                ('http/server_zones', ['server_zones']),
                ('http/upstreams', ['upstreams']),
                ('nginx', []),
                ('ssl', ['ssl']),
                ('http/caches', ['caches']),
                ('connections', ['connections']),
                ('slabs', ['slabs']),
            ],
        ),
    ],
)
def test_get_enabled_endpoints(check, instance_plus_v7, version, use_stream, expected_endpoints, caplog):
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    instance = deepcopy(instance_plus_v7)
    instance['use_plus_api_stream'] = use_stream
    instance['plus_api_version'] = version
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    assert sorted(check._get_enabled_endpoints()) == sorted(expected_endpoints)

    # Assert this log line is not emmitted because if it does then the method fell back to all endpoints
    assert "Could not determine available endpoints from the API" not in caplog.text

    LOG_LINES_TO_ASSERT = [
        "Querying base API url",
        "Querying http API url",
        "Available endpoints are",
        "Supported endpoints are",
    ]
    STREAM_LOG_LINE = "Querying stream API url"
    if use_stream:
        LOG_LINES_TO_ASSERT.append(STREAM_LOG_LINE)
    else:
        assert STREAM_LOG_LINE not in caplog.text

    for log_line in LOG_LINES_TO_ASSERT:
        assert log_line in caplog.text


@pytest.mark.parametrize("only_query_enabled_endpoints", [(True), (False)])
def test_only_query_enabled_endpoints(check, dd_run_check, instance_plus_v7, only_query_enabled_endpoints):
    instance = deepcopy(instance_plus_v7)
    instance['only_query_enabled_endpoints'] = only_query_enabled_endpoints
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)

    with mock.patch('datadog_checks.nginx.Nginx._get_enabled_endpoints') as get_enabled_endpoints:
        dd_run_check(check)
        assert only_query_enabled_endpoints == get_enabled_endpoints.called

    if only_query_enabled_endpoints:
        # Test only_query_enabled_endpoints works when stream metrics are not available
        # and new endpoints are added
        def mock_get_return(*args, **kwargs):
            response = mock.MagicMock()
            if args[0] == "http://{}:{}/api/7".format(HOST, PORT):
                response.json.return_value = [
                    "nginx",
                    "http",
                ]
            elif args[0] == "http://{}:{}/api/7/http".format(HOST, PORT):
                response.json.return_value = [
                    "requests",
                    "location_zonesthatarenew",
                ]
            elif args[0] == "http://{}:{}/api/7/stream".format(HOST, PORT):
                response.json.return_value = ["server_zones"]
            return response

        check._perform_request = mock.MagicMock(side_effect=mock_get_return)
        endpoints = check._get_enabled_endpoints()
        expected_endpoints = [('nginx', []), ('http/requests', ['requests'])]
        assert sorted(expected_endpoints) == sorted(endpoints)


@pytest.mark.parametrize(
    'test_input, expected_output',
    [
        (
            {
                '1': {
                    "stream/server_zones": ["stream", "server_zones"],
                    "stream/upstreams": ["stream", "upstreams"],
                },
                '3': {
                    "stream/zone_sync": ["stream", "zone_sync"],
                },
                '6': {
                    "stream/limit_conns": ["stream", "limit_conns"],
                },
            },
            ['stream/server_zones', 'stream/upstreams', 'stream/zone_sync', 'stream/limit_conns'],
        ),
        (
            {
                'foo': {"biz": ["stream1"], "buz": ["stream1", "stream2"], "bes": "stream3"},
                "baz": {"bux": "zone_sync", "bus": "zone_sync"},
                "bar": {
                    "bis": ["stream1", "stream2", "stream3"],
                },
            },
            ['biz', 'buz', 'bes', 'bux', 'bus', 'bis'],
        ),
    ],
)
def test_list_endpoints(instance, test_input, expected_output):
    nginx = Nginx('nginx', {}, [instance])
    # Python 2 seems to have some different order of processing the keys.
    # Sorting the arrays before comparison to account for this.
    sorted_test_output = nginx.list_endpoints(test_input).sort()
    assert eval(str(sorted_test_output)) == expected_output.sort()
