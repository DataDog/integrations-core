# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nginx import Nginx
from datadog_checks.nginx.metrics import COUNT_METRICS

from .common import ALL_PLUS_METRICS, CHECK_NAME, FIXTURES_PATH, TAGS
from .utils import mocked_perform_request


def _assert_all_metrics_and_metadata(aggregator):
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    for metric in ALL_PLUS_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()


def _assert_num_metrics(aggregator, num_expected):
    total = 0
    for m in aggregator.metric_names:
        total += len(aggregator.metrics(m))
    assert total == num_expected


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


def test_plus_api_v2(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 2

    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    _assert_num_metrics(aggregator, 1199)
    _assert_all_metrics_and_metadata(aggregator)


def test_plus_api_no_stream(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = False
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    _assert_num_metrics(aggregator, 891)
    _assert_all_metrics_and_metadata(aggregator)


def test_plus_api_v3(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 3
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    _assert_num_metrics(aggregator, 1210)
    _assert_all_metrics_and_metadata(aggregator)

    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone1', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone2', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total_count', 'zone:zone2', count=1)


def test_plus_api_v4(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 4
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    # total number of metrics should be same as v3
    _assert_num_metrics(aggregator, 1210)
    _assert_all_metrics_and_metadata(aggregator)


def test_plus_api_v5(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 5
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    # total number of metrics should be higher than v4 w/ resolvers and http location zones data
    _assert_num_metrics(aggregator, 1252)
    _assert_all_metrics_and_metadata(aggregator)

    base_tags = ['bar:bar', 'foo:foo']

    # resolvers endpoint
    resolvers_tags = base_tags + ['resolver:resolver-http']
    aggregator.assert_metric('nginx.resolver.responses.noerror', value=0, tags=resolvers_tags, count=1)

    # http location zones endpoint w/out code data
    location_zone_tags = base_tags + ['location_zone:swagger']
    location_zone_code_tags = location_zone_tags + ['code:404']

    aggregator.assert_metric(
        'nginx.location_zone.requests',
        value=2117,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=location_zone_tags,
        count=1,
    )
    aggregator.assert_metric(
        'nginx.location_zone.responses.code',
        value=21,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=location_zone_code_tags,
        count=0,
    )
    aggregator.assert_metric(
        'nginx.location_zone.responses.total',
        value=2117,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=location_zone_tags,
        count=1,
    )
    aggregator.assert_metric(
        'nginx.location_zone.responses.total',
        value=2117,
        metric_type=aggregator.GAUGE,
        tags=location_zone_tags,
        count=0,
    )

    # no limit conns endpoint
    conn_tags = base_tags + ['limit_conn:addr']
    aggregator.assert_metric(
        'nginx.stream.limit_conn.rejected', value=0, metric_type=aggregator.MONOTONIC_COUNT, tags=conn_tags, count=0
    )


def test_plus_api_v6(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 6
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    # total number of metrics should be higher than v5 w/ http limit conns, http limit reqs, and stream limit conns
    _assert_num_metrics(aggregator, 1268)
    _assert_all_metrics_and_metadata(aggregator)

    base_tags = ['bar:bar', 'foo:foo']

    # same tests for v3
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone1', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone2', count=1)

    # stream limit conns endpoint
    conn_tags = base_tags + ['limit_conn:addr']
    aggregator.assert_metric(
        'nginx.stream.limit_conn.rejected', value=0, metric_type=aggregator.MONOTONIC_COUNT, tags=conn_tags, count=1
    )

    # http limit conns endpoint
    aggregator.assert_metric(
        'nginx.limit_conn.rejected_dry_run',
        value=19864,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=conn_tags,
        count=1,
    )

    # http limit reqs endpoint
    limit_req_tags = base_tags + ['limit_req:one']
    aggregator.assert_metric(
        'nginx.limit_req.delayed_dry_run',
        value=322948,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=limit_req_tags,
        count=1,
    )

    # http server zones endpoint does not have code information
    code_tags = base_tags + ['code:200', 'server_zone:hg.nginx.org']
    aggregator.assert_metric(
        'nginx.server_zone.responses.code',
        value=803845,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=code_tags,
        count=0,
    )


def test_plus_api_v7(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 7
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    # total number of metrics should be higher than v6
    # with codes data for http upstream, http server zones, and http location zone
    _assert_num_metrics(aggregator, 1342)
    _assert_all_metrics_and_metadata(aggregator)

    base_tags = ['bar:bar', 'foo:foo']

    # same tests for v3
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone1', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone2', count=1)

    # http location zones endpoint
    location_zone_tags = base_tags + ['location_zone:swagger']
    location_zone_code_tags = location_zone_tags + ['code:404']

    aggregator.assert_metric(
        'nginx.location_zone.requests',
        value=1895,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=location_zone_tags,
        count=1,
    )
    aggregator.assert_metric(
        'nginx.location_zone.responses.code',
        value=1,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=location_zone_code_tags,
        count=1,
    )

    # http server zones endpoint
    code_tags = base_tags + ['code:200', 'server_zone:hg.nginx.org']
    aggregator.assert_metric(
        'nginx.server_zone.responses.code',
        value=803845,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=code_tags,
        count=1,
    )

    # http limit reqs endpoint
    limit_req_tags = base_tags + ['limit_req:one']
    aggregator.assert_metric(
        'nginx.limit_req.delayed_dry_run',
        value=322948,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=limit_req_tags,
        count=1,
    )

    # http upstreams endpoint
    upstream_tags = base_tags + ['server:10.0.0.42:8084', 'upstream:demo-backend']
    aggregator.assert_metric(
        'nginx.upstream.peers.health_checks.unhealthy_count',
        value=0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=upstream_tags,
        count=1,
    )
    aggregator.assert_metric(
        'nginx.upstream.peers.fails_count',
        value=4865455.0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=upstream_tags,
        count=1,
    )

    upstream_code_tags = base_tags + ['code:200', 'server:10.0.0.42:8084', 'upstream:demo-backend']
    aggregator.assert_metric(
        'nginx.upstream.peers.responses.code',
        value=12960954,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=upstream_code_tags,
        count=1,
    )

    # resolvers endpoint
    resolvers_tags = base_tags + ['resolver:resolver-http']
    aggregator.assert_metric(
        'nginx.resolver.responses.noerror',
        value=0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=resolvers_tags,
        count=1,
    )

    # stream limit conns endpoint
    conn_tags = base_tags + ['limit_conn:addr']
    aggregator.assert_metric(
        'nginx.stream.limit_conn.rejected', value=0, metric_type=aggregator.MONOTONIC_COUNT, tags=conn_tags, count=1
    )

    # http limit conns endpoint
    aggregator.assert_metric(
        'nginx.limit_conn.rejected_dry_run',
        value=19864,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=conn_tags,
        count=1,
    )

    # ensure all count metrics are submitted in v7
    for metric_name in COUNT_METRICS:
        aggregator.assert_metric(metric_name, at_least=1)


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

        http_wargs = dict(
            auth=mock.ANY,
            cert=mock.ANY,
            headers=mock.ANY,
            proxies=mock.ANY,
            timeout=mock.ANY,
            verify=mock.ANY,
            allow_redirects=mock.ANY,
        )
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
