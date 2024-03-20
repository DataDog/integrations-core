# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest

from datadog_checks.nginx.metrics import COUNT_METRICS

from .common import TAGS_WITH_HOST_AND_PORT, assert_all_metrics_and_metadata, assert_num_metrics
from .utils import mocked_perform_request

pytestmark = [pytest.mark.unit]


def test_plus_api_v2(check, instance_plus_v7, aggregator):
    instance = deepcopy(instance_plus_v7)
    instance['plus_api_version'] = 2

    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    assert_num_metrics(aggregator, 1208)


@pytest.mark.parametrize('only_query_enabled_endpoints', [True, False])
def test_plus_api_no_stream(check, instance_plus_v7_no_stream, aggregator, only_query_enabled_endpoints):
    instance = deepcopy(instance_plus_v7_no_stream)
    instance['plus_api_version'] = 2
    instance['only_query_enabled_endpoints'] = only_query_enabled_endpoints

    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    assert_num_metrics(aggregator, 895)


def test_plus_api_v3(check, instance_plus_v7, aggregator):
    instance = deepcopy(instance_plus_v7)
    instance['plus_api_version'] = 3
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    assert_num_metrics(aggregator, 1219)

    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone1', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone2', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total_count', 'zone:zone2', count=1)


def test_plus_api_v4(check, instance_plus_v7, aggregator):
    instance = deepcopy(instance_plus_v7)
    instance['plus_api_version'] = 4
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    # total number of metrics should be same as v3
    assert_num_metrics(aggregator, 1219)


def test_plus_api_v5(check, instance_plus_v7, aggregator):
    instance = deepcopy(instance_plus_v7)
    instance['plus_api_version'] = 5
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    # total number of metrics should be higher than v4 w/ resolvers and http location zones data
    assert_num_metrics(aggregator, 1261)

    # resolvers endpoint
    resolvers_tags = TAGS_WITH_HOST_AND_PORT + ['resolver:resolver-http']
    aggregator.assert_metric('nginx.resolver.responses.noerror', value=0, tags=resolvers_tags, count=1)

    # http location zones endpoint w/out code data
    location_zone_tags = TAGS_WITH_HOST_AND_PORT + ['location_zone:swagger']
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
    conn_tags = TAGS_WITH_HOST_AND_PORT + ['limit_conn:addr']
    aggregator.assert_metric(
        'nginx.stream.limit_conn.rejected', value=0, metric_type=aggregator.MONOTONIC_COUNT, tags=conn_tags, count=0
    )


def test_plus_api_v6(check, instance_plus_v7, aggregator):
    instance = deepcopy(instance_plus_v7)
    instance['plus_api_version'] = 6
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    # total number of metrics should be higher than v5 w/ http limit conns, http limit reqs, and stream limit conns
    assert_num_metrics(aggregator, 1277)

    # same tests for v3
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone1', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone2', count=1)

    # stream limit conns endpoint
    conn_tags = TAGS_WITH_HOST_AND_PORT + ['limit_conn:addr']
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
    limit_req_tags = TAGS_WITH_HOST_AND_PORT + ['limit_req:one']
    aggregator.assert_metric(
        'nginx.limit_req.delayed_dry_run',
        value=322948,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=limit_req_tags,
        count=1,
    )

    # http server zones endpoint does not have code information
    code_tags = TAGS_WITH_HOST_AND_PORT + ['code:200', 'server_zone:hg.nginx.org']
    aggregator.assert_metric(
        'nginx.server_zone.responses.code',
        value=803845,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=code_tags,
        count=0,
    )


@pytest.mark.parametrize('only_query_enabled_endpoints', [(True), (False)])
def test_plus_api_v7(check, instance_plus_v7, aggregator, only_query_enabled_endpoints):
    instance = deepcopy(instance_plus_v7)
    instance['only_query_enabled_endpoints'] = only_query_enabled_endpoints
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    # total number of metrics should be higher than v6
    # with codes data for http upstream, http server zones, and http location zone
    assert_num_metrics(aggregator, 1352)

    # same tests for v3
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone1', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone2', count=1)

    # http location zones endpoint
    location_zone_tags = TAGS_WITH_HOST_AND_PORT + ['location_zone:swagger']
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
    code_tags = TAGS_WITH_HOST_AND_PORT + ['code:200', 'server_zone:hg.nginx.org']
    aggregator.assert_metric(
        'nginx.server_zone.responses.code',
        value=803845,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=code_tags,
        count=1,
    )

    # http limit reqs endpoint
    limit_req_tags = TAGS_WITH_HOST_AND_PORT + ['limit_req:one']
    aggregator.assert_metric(
        'nginx.limit_req.delayed_dry_run',
        value=322948,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=limit_req_tags,
        count=1,
    )

    # http upstreams endpoint
    upstream_tags = TAGS_WITH_HOST_AND_PORT + ['server:10.0.0.42:8084', 'upstream:demo-backend']
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

    upstream_code_tags = TAGS_WITH_HOST_AND_PORT + ['code:200', 'server:10.0.0.42:8084', 'upstream:demo-backend']
    aggregator.assert_metric(
        'nginx.upstream.peers.responses.code',
        value=12960954,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=upstream_code_tags,
        count=1,
    )

    # resolvers endpoint
    resolvers_tags = TAGS_WITH_HOST_AND_PORT + ['resolver:resolver-http']
    aggregator.assert_metric(
        'nginx.resolver.responses.noerror',
        value=0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=resolvers_tags,
        count=1,
    )

    # stream limit conns endpoint
    conn_tags = TAGS_WITH_HOST_AND_PORT + ['limit_conn:addr']
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


def test_plus_api_v7_no_stream(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = False
    instance['plus_api_version'] = 7
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    assert_all_metrics_and_metadata(aggregator)
    # Number of metrics should be low since stream is disabled
    assert_num_metrics(aggregator, 1025)

    # test that stream metrics are not emitted
    aggregator.assert_metric('nginx.stream.zone_sync.zone.records_total', count=0)
    aggregator.assert_metric('nginx.stream.limit_conn.rejected', count=0)

    # http server zones endpoint
    code_tags = TAGS_WITH_HOST_AND_PORT + ['code:200', 'server_zone:hg.nginx.org']
    aggregator.assert_metric(
        'nginx.server_zone.responses.code',
        value=803845,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=code_tags,
        count=1,
    )

    # http upstreams endpoint
    upstream_tags = TAGS_WITH_HOST_AND_PORT + ['server:10.0.0.42:8084', 'upstream:demo-backend']
    aggregator.assert_metric(
        'nginx.upstream.peers.health_checks.unhealthy_count',
        value=0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=upstream_tags,
        count=1,
    )
