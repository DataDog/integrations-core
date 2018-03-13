import pytest

from datadog_checks.envoy.errors import UnknownMetric
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS
from datadog_checks.envoy.parser import parse_metric, reassemble_addresses


class TestReassembleAddresses:
    def test_correct(self):
        seq = ['0', '0', '0', '0_80', 'ingress_http']
        assert reassemble_addresses(seq) == ['0.0.0.0:80', 'ingress_http']

    def test_reassemble_addresses_empty(self):
        assert reassemble_addresses([]) == []


class TestParseMetric:
    def test_unknown(self):
        with pytest.raises(UnknownMetric):
            parse_metric('foo.bar')

    def test_runtime(self):
        metric = 'runtime.num_keys'
        tags = METRICS[metric]['tags']

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_cds(self):
        metric = 'cluster_manager.cds.config_reload'
        tags = METRICS[metric]['tags']

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_http_router_filter(self):
        metric = 'http{}.rq_total'
        untagged_metric = metric.format('')
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
        tag0 = '0.0.0.0_80'
        tag0_reassembled = tag0.replace('_', ':')
        tag1 = 'some_cipher'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0_reassembled), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_listener_manager(self):
        metric = 'listener_manager.listener_added'
        tags = METRICS[metric]['tags']

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_http(self):
        metric = 'http{}.downstream_cx_total'
        untagged_metric = metric.format('')
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
        tag0 = '0.0.0.0_80'
        tag0_reassembled = tag0.replace('_', ':')
        tag1 = 'some_stat_prefix'
        tagged_metric = metric.format('.{}'.format(tag0), '.{}'.format(tag1))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0_reassembled), '{}:{}'.format(tags[1], tag1)],
            METRICS[untagged_metric]['method']
        )

    def test_http2(self):
        metric = 'http2.rx_reset'
        tags = METRICS[metric]['tags']

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_cluster_manager(self):
        metric = 'cluster_manager.cluster_added'
        tags = METRICS[metric]['tags']

        assert parse_metric(metric) == (
            METRIC_PREFIX + metric,
            list(tags),
            METRICS[metric]['method']
        )

    def test_cluster(self):
        metric = 'cluster{}.upstream_cx_total'
        untagged_metric = metric.format('')
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
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
        tags = METRICS[untagged_metric]['tags']
        tag0 = 'some_name'
        tagged_metric = metric.format('.{}'.format(tag0))

        assert parse_metric(tagged_metric) == (
            METRIC_PREFIX + untagged_metric,
            ['{}:{}'.format(tags[0], tag0)],
            METRICS[untagged_metric]['method']
        )
