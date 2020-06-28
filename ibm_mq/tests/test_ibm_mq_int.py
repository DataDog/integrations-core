# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
from pymqi.CMQC import MQGMO_BROWSE_NEXT, MQOO_BROWSE
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics, running_on_ci
from datadog_checks.ibm_mq import IbmMqCheck
from datadog_checks.ibm_mq.collectors.stats_collector import QUEUE_GET_OPTIONS, QUEUE_OPTIONS

from . import common
from .common import CHANNEL_STATS_METRICS, QUEUE_METRICS, QUEUE_STATS_METRICS, assert_all_metrics

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


def test_check_metrics_and_service_checks(aggregator, instance, seed_data):
    instance['mqcd_version'] = os.getenv('IBM_MQ_VERSION')
    check = IbmMqCheck('ibm_mq', {}, [instance])

    check.check(instance)

    assert_all_metrics(aggregator)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'mq_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
        'connection_name:{}({})'.format(common.HOST, common.PORT),
        'foo:bar',
    ]

    channel_tags = tags + ['channel:{}'.format(common.CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.OK, tags=channel_tags, count=1)

    bad_channel_tags = tags + ['channel:{}'.format(common.BAD_CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.CRITICAL, tags=bad_channel_tags, count=1)

    discoverable_tags = tags + ['channel:*']
    aggregator.assert_service_check('ibm_mq.channel', check.OK, tags=discoverable_tags, count=1)


def test_stats_metrics(aggregator, instance, seed_data):
    instance['mqcd_version'] = os.getenv('IBM_MQ_VERSION')
    instance['collect_statistics_metrics'] = True
    check = IbmMqCheck('ibm_mq', {}, [instance])

    # local: only browse, so that the test can run multiple time.
    # ci: no browse, this test can/should only run once
    if running_on_ci():
        check.check(instance)
    else:
        with mock.patch(
            'datadog_checks.ibm_mq.collectors.stats_collector.QUEUE_GET_OPTIONS', QUEUE_GET_OPTIONS | MQGMO_BROWSE_NEXT
        ), mock.patch('datadog_checks.ibm_mq.collectors.stats_collector.QUEUE_OPTIONS', QUEUE_OPTIONS | MQOO_BROWSE):
            check.check(instance)

    for metric, metric_type in QUEUE_STATS_METRICS:
        aggregator.assert_metric_has_tag_prefix(metric, 'queue:')
        aggregator.assert_metric_has_tag_prefix(metric, 'queue_type:')
        aggregator.assert_metric_has_tag_prefix(metric, 'definition_type:')
        aggregator.assert_metric(metric, metric_type=getattr(aggregator, metric_type.upper()))

    tag_groups = [
        ['channel:GCP.A', 'channel_type:clusrcvr', 'connection_name:192.168.208.2', 'remote_q_mgr_name:QM2'],
        ['channel:GCP.B', 'channel_type:clussdr', 'connection_name:192.168.208.2(1414)', 'remote_q_mgr_name:QM2'],
    ]
    for tags in tag_groups:
        aggregator.assert_metric('ibm_mq.stats.channel.msgs', metric_type=aggregator.GAUGE, tags=tags)

    for metric, metric_type in CHANNEL_STATS_METRICS:
        aggregator.assert_metric_has_tag_prefix(metric, 'channel:')
        aggregator.assert_metric_has_tag_prefix(metric, 'channel_type:')
        aggregator.assert_metric_has_tag_prefix(metric, 'remote_q_mgr_name:')
        aggregator.assert_metric_has_tag_prefix(metric, 'connection_name:')
        aggregator.assert_metric(metric, metric_type=getattr(aggregator, metric_type.upper()))

    assert_all_metrics(aggregator)


def test_check_connection_name_one(aggregator, instance_with_connection_name):
    instance_with_connection_name['mqcd_version'] = os.getenv('IBM_MQ_VERSION')

    check = IbmMqCheck('ibm_mq', {}, [instance_with_connection_name])
    check.check(instance_with_connection_name)

    assert_all_metrics(aggregator)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'connection_name:{}({})'.format(common.HOST, common.PORT),
    ]

    channel_tags = tags + ['channel:{}'.format(common.CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.OK, tags=channel_tags, count=1)


def test_check_connection_names_multi(aggregator, instance_with_connection_name):
    instance = instance_with_connection_name
    instance['mqcd_version'] = os.getenv('IBM_MQ_VERSION')
    instance['connection_name'] = "localhost(9999),{}".format(instance['connection_name'])

    check = IbmMqCheck('ibm_mq', {}, [instance])
    check.check(instance)

    assert_all_metrics(aggregator)


def test_check_all(aggregator, instance_collect_all, seed_data):
    check = IbmMqCheck('ibm_mq', {}, [instance_collect_all])
    check.check(instance_collect_all)

    assert_all_metrics(aggregator)


@pytest.mark.parametrize(
    'channel_status_mapping, expected_service_check_status',
    [({'running': 'warning'}, AgentCheck.WARNING), ({'running': 'critical'}, AgentCheck.CRITICAL)],
)
def test_integration_custom_mapping(aggregator, instance, channel_status_mapping, expected_service_check_status):
    instance['channel_status_mapping'] = channel_status_mapping
    check = IbmMqCheck('ibm_mq', {}, [instance])

    check.check(instance)

    aggregator.assert_service_check('ibm_mq.channel.status', expected_service_check_status)


def test_check_queue_pattern(aggregator, instance_queue_pattern, seed_data):
    check = IbmMqCheck('ibm_mq', {}, [instance_queue_pattern])
    check.check(instance_queue_pattern)

    assert_all_metrics(aggregator)


def test_check_queue_regex(aggregator, instance_queue_regex, seed_data):
    check = IbmMqCheck('ibm_mq', {}, [instance_queue_regex])
    check.check(instance_queue_regex)

    assert_all_metrics(aggregator)


def test_check_channel_count(aggregator, instance_queue_regex_tag, seed_data):
    # Late import to not require it for e2e
    import pymqi

    metrics_to_assert = {
        "inactive": 0,
        "binding": 0,
        "starting": 0,
        "running": 1,
        "stopping": 0,
        "retrying": 0,
        "stopped": 0,
        "requesting": 0,
        "paused": 0,
        "initializing": 0,
        "unknown": 0,
    }

    check = IbmMqCheck('ibm_mq', {}, [instance_queue_regex_tag])
    check.channel_metric_collector._submit_channel_count(
        'my_channel', pymqi.CMQCFC.MQCHS_RUNNING, ["channel:my_channel"]
    )

    for status, expected_value in iteritems(metrics_to_assert):
        aggregator.assert_metric(
            'ibm_mq.channel.count', expected_value, tags=["channel:my_channel", "status:" + status]
        )
    aggregator.assert_metric('ibm_mq.channel.count', 0, tags=["channel:my_channel", "status:unknown"])


def test_check_channel_count_status_unknown(aggregator, instance_queue_regex_tag, seed_data):
    metrics_to_assert = {
        "inactive": 0,
        "binding": 0,
        "starting": 0,
        "running": 0,
        "stopping": 0,
        "retrying": 0,
        "stopped": 0,
        "requesting": 0,
        "paused": 0,
        "initializing": 0,
        "unknown": 1,
    }

    check = IbmMqCheck('ibm_mq', {}, [instance_queue_regex_tag])
    check.channel_metric_collector._submit_channel_count('my_channel', 123, ["channel:my_channel"])

    for status, expected_value in iteritems(metrics_to_assert):
        aggregator.assert_metric(
            'ibm_mq.channel.count', expected_value, tags=["channel:my_channel", "status:" + status]
        )


def test_check_regex_tag(aggregator, instance_queue_regex_tag, seed_data):
    check = IbmMqCheck('ibm_mq', {}, [instance_queue_regex_tag])
    check.check(instance_queue_regex_tag)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'mq_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
        'connection_name:{}({})'.format(common.HOST, common.PORT),
        'channel:{}'.format(common.CHANNEL),
        'queue:{}'.format(common.QUEUE),
        'foo:bar',
    ]

    for metric, _ in QUEUE_METRICS:
        aggregator.assert_metric(metric, tags=tags)


def test_collect_statistics_from_events(aggregator, instance):
    instance['mqcd_version'] = '9'
    check = IbmMqCheck('ibm_mq', {}, [instance])

    check.check(instance)

    assert_all_metrics(aggregator)


def test_channel_stats_metrics(aggregator, instance):
    instance['mqcd_version'] = os.getenv('IBM_MQ_VERSION')

    check = IbmMqCheck('ibm_mq', {}, [instance])
    check.channel_metric_collector = mock.MagicMock()
    check.queue_metric_collector = mock.MagicMock()

    with open(os.path.join(common.HERE, 'fixtures', 'statistics_channel.data'), 'rb') as f:
        statistics_channel = f.read()
        with mock.patch('datadog_checks.ibm_mq.collectors.stats_collector.Queue') as queue:
            queue().get.return_value = statistics_channel

            check.check(instance)

    tags = [
        'channel:GCP.A',
        'channel_type:clusrcvr',
        'remote_q_mgr_name:QM2',
        'connection_name:192.168.32.2',
    ]
    for metric, metric_type in common.CHANNEL_STATS_METRICS:
        aggregator.assert_metric(metric, tags=tags)
        aggregator.assert_metric(metric, metric_type=getattr(aggregator, metric_type.upper()), tags=tags)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
