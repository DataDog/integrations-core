# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest
from packaging import version
from requests import HTTPError

from datadog_checks.consul import ConsulCheck
from datadog_checks.dev.utils import get_metadata_metrics

from . import common
from .common import CONSUL_VERSION, PROMETHEUS_HIST_METRICS_1_9, PROMETHEUS_METRICS_1_9

METRICS = [
    'consul.catalog.nodes_up',
    'consul.catalog.nodes_passing',
    'consul.catalog.nodes_warning',
    'consul.catalog.nodes_critical',
    'consul.catalog.services_up',
    'consul.catalog.services_passing',
    'consul.catalog.services_warning',
    'consul.catalog.services_critical',
    'consul.catalog.services_count',
    'consul.catalog.total_nodes',
]


MULTI_NODE_METRICS = [
    'consul.net.node.latency.p95',
    'consul.net.node.latency.min',
    'consul.net.node.latency.p25',
    'consul.net.node.latency.median',
    'consul.net.node.latency.max',
    'consul.net.node.latency.p99',
    'consul.net.node.latency.p90',
    'consul.net.node.latency.p75',
]


@pytest.mark.integration
def test_check(aggregator, instance, dd_environment):
    """
    Testing Consul Integration
    """
    consul_check = ConsulCheck(common.CHECK_NAME, {}, [instance])
    consul_check.check(instance)

    for m in METRICS + MULTI_NODE_METRICS:
        aggregator.assert_metric(m, at_least=0)

    aggregator.assert_metric('consul.peers', value=3)

    aggregator.assert_service_check('consul.check')
    aggregator.assert_service_check('consul.up', tags=['consul_datacenter:dc1', 'consul_url:{}'.format(common.URL)])

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_single_node_install(aggregator, instance_single_node_install, dd_environment):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, [instance_single_node_install])
    consul_check.check(instance_single_node_install)

    for m in METRICS:
        aggregator.assert_metric(m, at_least=1)

    aggregator.assert_metric('consul.peers', value=3)

    aggregator.assert_service_check('consul.check')
    aggregator.assert_service_check('consul.up', tags=['consul_datacenter:dc1', 'consul_url:{}'.format(common.URL)])

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_acl_forbidden(instance_bad_token, dd_environment):
    """
    Testing Consul Integration with wrong ACL token
    """
    consul_check = ConsulCheck(common.CHECK_NAME, {}, [instance_bad_token])

    got_error_403 = False
    try:
        consul_check.check(None)
    except HTTPError as e:
        if e.response.status_code == 403:
            got_error_403 = True

    assert got_error_403


@pytest.mark.integration
def test_prometheus_endpoint(aggregator, dd_environment, instance_prometheus, caplog):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, [instance_prometheus])
    common_tags = instance_prometheus['tags']
    greater_than_1_6 = version.parse(CONSUL_VERSION) > version.parse('1.6.0')

    if not common.PROMETHEUS_ENDPOINT_AVAILABLE:
        caplog.at_level(logging.WARNING)
        consul_check.check(instance_prometheus)
        assert (
            "does not support the prometheus endpoint. "
            "Update Consul or set back `use_prometheus_endpoint` to false to remove this warning." in caplog.text
        )
        return

    consul_check.check(instance_prometheus)

    aggregator.assert_service_check(
        'consul.prometheus.health',
        tags=common_tags + ['endpoint:{}/v1/agent/metrics?format=prometheus'.format(common.URL)],
    )

    for metric in common.PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, tags=common_tags, count=1)

    if greater_than_1_6:
        for metric in PROMETHEUS_METRICS_1_9:
            aggregator.assert_metric(metric, tags=common_tags, count=1)

    aggregator.assert_metric('consul.memberlist.msg.suspect', tags=common_tags, at_least=0)
    aggregator.assert_metric('consul.peers', value=3, count=1)
    if greater_than_1_6:
        aggregator.assert_metric_has_tag_prefix('consul.raft.replication.appendEntries.logs', 'peer_id', count=2)

    for hist_suffix in ['count', 'sum', 'quantile']:
        aggregator.assert_metric_has_tag('consul.http.request.{}'.format(hist_suffix), 'method:GET', at_least=0)
        for tag in common_tags:
            aggregator.assert_metric_has_tag('consul.raft.leader.lastContact.' + hist_suffix, tag, at_least=0)
            for metric in common.PROMETHEUS_HIST_METRICS:
                aggregator.assert_metric_has_tag(metric + hist_suffix, tag, at_least=1)
            if greater_than_1_6:
                for metric in PROMETHEUS_HIST_METRICS_1_9:
                    aggregator.assert_metric_has_tag(metric + hist_suffix, tag, at_least=1)
                aggregator.assert_metric_has_tag('consul.raft.replication.heartbeat.' + hist_suffix, tag, at_least=1)

    # Some of the metrics documented in the metadata.csv were sent through DogStatsD as `timer` as well.
    # We end up with some of the prometheus metrics having a different in-app type.
    # Example with `consul.raft.commitTime.count`:
    #  * It is a rate when submitting metrics with DogStatsD
    #  * It is a rate when submitting metrics with OpenMetricsBaseCheck
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
def test_version_metadata(aggregator, instance, dd_environment, datadog_agent):
    consul_check = ConsulCheck(common.CHECK_NAME, {}, [instance])
    consul_check.check_id = 'test:123'
    consul_check.check(instance)

    raw_version = common.CONSUL_VERSION.lstrip('v')  # some versions contain `v` prefix
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
