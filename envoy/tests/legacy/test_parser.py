# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.envoy.errors import UnknownMetric, UnknownTags
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS
from datadog_checks.envoy.parser import parse_histogram, parse_metric

pytestmark = [pytest.mark.unit]


def test_unknown_metric():
    with pytest.raises(UnknownMetric):
        parse_metric('foo.bar')


def test_unknown_tag():
    with pytest.raises(UnknownTags):
        parse_metric('stats.major.overflow')


def test_runtime():
    metric = 'runtime.num_keys'
    tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

    assert parse_metric(metric) == (METRIC_PREFIX + metric, list(tags), METRICS[metric]['method'])


def test_cds():
    metric = 'cluster_manager.cds.config_reload'
    tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

    assert parse_metric(metric) == (METRIC_PREFIX + metric, list(tags), METRICS[metric]['method'])


def test_retry_metric():
    metric = "cluster{}.upstream_cx_total"
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'service-foo.default.eu-west-3-prd.internal.a4d363d6-a669-b02c-a274-52c1df12bd41.consul'
    tagged_metric = metric.format('.{}'.format(tag0))
    assert parse_metric(tagged_metric, retry=True, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_retry_invalid_metric():
    with pytest.raises(UnknownMetric):
        parse_metric(
            "cluster.ms-catalog-category-appli.default.eu-west-3-stg.internal"
            ".ba3374ca-fb2a-3f3e-9ea6-79e021188673.consul.http2.dropped_headers_with_underscores",
            retry=True,
        )


def test_http_router_filter():
    metric = 'http{}.rq_total'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_http_router_filter_vhost():
    metric = 'vhost{}.vcluster{}.upstream_rq_time'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_vhost_name'
    tag1 = 'some_vcluster_name'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )

    # Legacy tag
    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1), 'virtual_cluster_name:{}'.format(tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_http_rate_limit():
    metric = 'cluster{}.ratelimit.ok'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_route_target_cluster'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_ip_tagging():
    metric = 'http{}.ip_tagging{}.hit'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_tag_name'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_grpc():
    metric = 'cluster{}.grpc{}{}.total'
    untagged_metric = metric.format('', '', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_route_target_cluster'
    tag1 = 'some_grpc_service'
    tag2 = 'some_grpc_method'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1), '.{}'.format(tag2))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1), '{}:{}'.format(tags[2], tag2)],
        METRICS[untagged_metric]['method'],
    )


def test_dynamodb_operation():
    metric = 'http{}.dynamodb.operation{}.upstream_rq_total'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_operation_name'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_dynamodb_table():
    metric = 'http{}.dynamodb.table{}.upstream_rq_total'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_table_name'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_dynamodb_error():
    metric = 'http{}.dynamodb.error{}{}'
    untagged_metric = metric.format('', '', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_table_name'
    tag2 = 'error_type'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1), '.{}'.format(tag2))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1), '{}:{}'.format(tags[2], tag2)],
        METRICS[untagged_metric]['method'],
    )


def test_http_buffer_filter():
    metric = 'http{}.buffer.rq_timeout'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_rds():
    metric = 'http{}.rds{}.config_reload'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_route_config_name'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_tcp_proxy():
    metric = 'tcp{}.downstream_cx_total'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_tls():
    metric = 'auth.clientssl{}.update_success'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_network_rate_limit():
    metric = 'ratelimit{}.total'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_redis():
    metric = 'redis{}.downstream_rq_total'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_redis_splitter():
    metric = 'redis{}.splitter.invalid_request'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_redis_command():
    metric = 'redis{}.command{}.total'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_command'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_mongo():
    metric = 'mongo{}.op_insert'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_mongo_command():
    metric = 'mongo{}.cmd{}.total'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_command'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_mongo_collection():
    metric = 'mongo{}.collection{}.query.total'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_collection'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_listener():
    metric = 'listener{}.ssl.ciphers{}'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = '0.0.0.0_80'
    tag1 = 'some_ciphers'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_listener_manager():
    metric = 'listener_manager.listener_added'
    tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

    assert parse_metric(metric) == (METRIC_PREFIX + metric, list(tags), METRICS[metric]['method'])


def test_listener_tls():
    metric = 'listener{}.ssl.versions{}'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = '0.0.0.0'
    tag1 = 'TLSv1.2'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_listener_curves():
    metric = 'listener{}.ssl.curves{}'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = '0.0.0.0'
    tag1 = 'P-256'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_listener_sigalgs():
    metric = 'listener{}.ssl.sigalgs{}'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = '0.0.0.0'
    tag1 = 'rsa_pss_rsae_sha256'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_http():
    metric = 'http{}.downstream_cx_total'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_http_user_agent():
    metric = 'http{}.user_agent{}.downstream_cx_total'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_stat_prefix'
    tag1 = 'some_user_agent'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_http_listener():
    metric = 'listener{}.http{}.downstream_rq_2xx'
    untagged_metric = metric.format('', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = '0.0.0.0_80'
    tag1 = 'some_stat_prefix'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
        METRICS[untagged_metric]['method'],
    )


def test_http2():
    metric = 'http2.rx_reset'
    tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

    assert parse_metric(metric) == (METRIC_PREFIX + metric, list(tags), METRICS[metric]['method'])


def test_cluster_manager():
    metric = 'cluster_manager.cluster_added'
    tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

    assert parse_metric(metric) == (METRIC_PREFIX + metric, list(tags), METRICS[metric]['method'])


def test_cluster():
    metric = 'cluster{}.upstream_cx_total'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_name'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )

    # Legacy tag
    assert parse_metric(tagged_metric) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), 'cluster_name:{}'.format(tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_cluster_health_check():
    metric = 'cluster{}.health_check.healthy'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_name'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_cluster_outlier_detection():
    metric = 'cluster{}.outlier_detection.ejections_enforced_total'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_name'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_cluster_dynamic_http():
    metric = 'cluster{}.upstream_rq_time'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_name'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_cluster_dynamic_http_zones():
    metric = 'cluster{}.zone{}{}.upstream_rq_time'
    untagged_metric = metric.format('', '', '')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_name'
    tag1 = 'some_table_name'
    tag2 = 'some_to_zone'
    tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1), '.{}'.format(tag2))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1), '{}:{}'.format(tags[2], tag2)],
        METRICS[untagged_metric]['method'],
    )


def test_cluster_load_balancer():
    metric = 'cluster{}.lb_healthy_panic'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_name'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_cluster_load_balancer_subsets():
    metric = 'cluster{}.lb_subsets_active'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'some_name'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_tag_with_dots():
    metric = 'cluster{}.lb_healthy_panic'
    untagged_metric = metric.format('')
    tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
    tag0 = 'out.alerting-event-evaluator-test.datadog.svc.cluster.local|iperf'
    tagged_metric = metric.format('.{}'.format(tag0))

    assert parse_metric(tagged_metric, disable_legacy_cluster_tag=True) == (
        METRIC_PREFIX + untagged_metric,
        ['{}:{}'.format(tags[0], tag0)],
        METRICS[untagged_metric]['method'],
    )


def test_no_match():
    metric = 'envoy.http.downstream_rq_time'
    value = 'No recorded values'

    assert list(parse_histogram(metric, value)) == []


def test_ignore_nan():
    metric = 'envoy.http.downstream_rq_time'
    value = 'P0(0,0) P25(nan,0)'

    assert list(parse_histogram(metric, value)) == [('envoy.http.downstream_rq_time.0percentile', 0.0)]


def test_correct():
    metric = 'envoy.http.downstream_rq_time'
    value = (
        'P0(0,0) P25(25,0) P50(50,0) P75(75,0) P90(90,1.06) P95(95,1.08) '
        'P99(99,1.096) P99.9(99.9,1.0996) P100(100,1.1)'
    )

    assert list(parse_histogram(metric, value)) == [
        ('envoy.http.downstream_rq_time.0percentile', 0.0),
        ('envoy.http.downstream_rq_time.25percentile', 25.0),
        ('envoy.http.downstream_rq_time.50percentile', 50.0),
        ('envoy.http.downstream_rq_time.75percentile', 75.0),
        ('envoy.http.downstream_rq_time.90percentile', 90.0),
        ('envoy.http.downstream_rq_time.95percentile', 95.0),
        ('envoy.http.downstream_rq_time.99percentile', 99.0),
        ('envoy.http.downstream_rq_time.99_9percentile', 99.9),
        ('envoy.http.downstream_rq_time.100percentile', 100.0),
    ]


def test_correct_unknown_percentile():
    metric = 'envoy.http.downstream_rq_time'
    value = 'P0(0,0) P25(25,0) P55.5(55.5,0)'

    assert list(parse_histogram(metric, value)) == [
        ('envoy.http.downstream_rq_time.0percentile', 0.0),
        ('envoy.http.downstream_rq_time.25percentile', 25.0),
        ('envoy.http.downstream_rq_time.55_5percentile', 55.5),
    ]
