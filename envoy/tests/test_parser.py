import pytest

from datadog_checks.envoy.errors import UnknownMetric, UnknownTags
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS
from datadog_checks.envoy.parser import parse_histogram, parse_metric


class TestParseMetric:
    def test_unknown_metric(self):
        with pytest.raises(UnknownMetric):
            parse_metric('foo.bar')

    def test_unknown_tag(self):
        with pytest.raises(UnknownTags):
            parse_metric('stats.major.overflow')

    def test_runtime(self):
        metric = 'runtime.num_keys'
        tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_cds(self):
        metric = 'cluster_manager.cds.config_reload'
        tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_http_router_filter(self):
        metric = 'http{}.rq_total'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_http_router_filter_vhost(self):
        metric = 'vhost{}.vcluster{}.upstream_rq_time'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_vhost_name'
        tag1 = 'some_vcluster_name'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_http_rate_limit(self):
        metric = 'cluster{}.ratelimit.ok'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_route_target_cluster'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_ip_tagging(self):
        metric = 'http{}.ip_tagging{}.hit'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_tag_name'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_grpc(self):
        metric = 'cluster{}.grpc{}{}.total'
        untagged_metric = metric.format('', '', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_route_target_cluster'
        tag1 = 'some_grpc_service'
        tag2 = 'some_grpc_method'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1), '.{}'.format(tag2))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1), '{}:{}'.format(tags[2], tag2)],
            METRICS[untagged_metric]['method']
        )

    def test_dynamodb_operation(self):
        metric = 'http{}.dynamodb.operation{}.upstream_rq_total'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_operation_name'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_dynamodb_table(self):
        metric = 'http{}.dynamodb.table{}.upstream_rq_total'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_table_name'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_dynamodb_error(self):
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
            METRICS[untagged_metric]['method']
        )

    def test_http_buffer_filter(self):
        metric = 'http{}.buffer.rq_timeout'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_rds(self):
        metric = 'http{}.rds{}.config_reload'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_route_config_name'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_tcp_proxy(self):
        metric = 'tcp{}.downstream_cx_total'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_tls(self):
        metric = 'auth.clientssl{}.update_success'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_network_rate_limit(self):
        metric = 'ratelimit{}.total'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_redis(self):
        metric = 'redis{}.downstream_rq_total'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_redis_splitter(self):
        metric = 'redis{}.splitter.invalid_request'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_redis_command(self):
        metric = 'redis{}.command{}.total'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_command'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_mongo(self):
        metric = 'mongo{}.op_insert'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_mongo_command(self):
        metric = 'mongo{}.cmd{}.total'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_command'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_mongo_collection(self):
        metric = 'mongo{}.collection{}.query.total'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_collection'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_listener(self):
        metric = 'listener{}.ssl.cipher{}'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = '0.0.0.0_80'
        tag1 = 'some_cipher'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_listener_manager(self):
        metric = 'listener_manager.listener_added'
        tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_http(self):
        metric = 'http{}.downstream_cx_total'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_http_user_agent(self):
        metric = 'http{}.user_agent{}.downstream_cx_total'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_stat_prefix'
        tag1 = 'some_user_agent'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_http_listener(self):
        metric = 'listener{}.http{}.downstream_rq_2xx'
        untagged_metric = metric.format('', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = '0.0.0.0_80'
        tag1 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_http2(self):
        metric = 'http2.rx_reset'
        tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_cluster_manager(self):
        metric = 'cluster_manager.cluster_added'
        tags = [tag for tags in METRICS[metric]['tags'] for tag in tags]

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_cluster(self):
        metric = 'cluster{}.upstream_cx_total'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_name'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_cluster_health_check(self):
        metric = 'cluster{}.health_check.healthy'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_name'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_cluster_outlier_detection(self):
        metric = 'cluster{}.outlier_detection.ejections_enforced_total'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_name'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_cluster_dynamic_http(self):
        metric = 'cluster{}.upstream_rq_time'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_name'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_cluster_dynamic_http_zones(self):
        metric = 'cluster{}.zone{}{}.upstream_rq_time'
        untagged_metric = metric.format('', '', '')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_name'
        tag1 = 'some_table_name'
        tag2 = 'some_to_zone'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1), '.{}'.format(tag2))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0), '{}:{}'.format(tags[1], tag1), '{}:{}'.format(tags[2], tag2)],
            METRICS[untagged_metric]['method']
        )

    def test_cluster_load_balancer(self):
        metric = 'cluster{}.lb_healthy_panic'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_name'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_cluster_load_balancer_subsets(self):
        metric = 'cluster{}.lb_subsets_active'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'some_name'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )

    def test_tag_with_dots(self):
        metric = 'cluster{}.lb_healthy_panic'
        untagged_metric = metric.format('')
        tags = [tag for tags in METRICS[untagged_metric]['tags'] for tag in tags]
        tag0 = 'out.alerting-event-evaluator-test.datadog.svc.cluster.local|iperf'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )


class TestParseHistogram:
    def test_no_match(self):
        metric = 'envoy.http.downstream_rq_time'
        value = 'No recorded values'

        assert list(parse_histogram(metric, value)) == []

    def test_ignore_nan(self):
        metric = 'envoy.http.downstream_rq_time'
        value = 'P0(0,0) P25(nan,0)'

        assert list(parse_histogram(metric, value)) == [
            ('envoy.http.downstream_rq_time.0percentile', 0.0),
        ]

    def test_correct(self):
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

    def test_correct_unknown_percentile(self):
        metric = 'envoy.http.downstream_rq_time'
        value = 'P0(0,0) P25(25,0) P55.5(55.5,0)'

        assert list(parse_histogram(metric, value)) == [
            ('envoy.http.downstream_rq_time.0percentile', 0.0),
            ('envoy.http.downstream_rq_time.25percentile', 25.0),
            ('envoy.http.downstream_rq_time.55_5percentile', 55.5),
        ]
