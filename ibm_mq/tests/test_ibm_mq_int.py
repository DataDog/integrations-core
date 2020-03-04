# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.ibm_mq import IbmMqCheck

from . import common
from .common import QUEUE_METRICS, assert_all_metrics

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


def test_check_metrics_and_service_checks(aggregator, instance, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance)

    assert_all_metrics(aggregator)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'mq_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
    ]

    channel_tags = tags + ['channel:{}'.format(common.CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.OK, tags=channel_tags, count=1)

    bad_channel_tags = tags + ['channel:{}'.format(common.BAD_CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.CRITICAL, tags=bad_channel_tags, count=1)

    discoverable_tags = tags + ['channel:*']
    aggregator.assert_service_check('ibm_mq.channel', check.OK, tags=discoverable_tags, count=1)


def test_check_all(aggregator, instance_collect_all, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
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
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_queue_pattern)

    assert_all_metrics(aggregator)


def test_check_queue_regex(aggregator, instance_queue_regex, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
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

    check = IbmMqCheck('ibm_mq', {}, {})
    check._submit_channel_count('my_channel', pymqi.CMQCFC.MQCHS_RUNNING, ["channel:my_channel"])

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

    check = IbmMqCheck('ibm_mq', {}, {})
    check._submit_channel_count('my_channel', 123, ["channel:my_channel"])

    for status, expected_value in iteritems(metrics_to_assert):
        aggregator.assert_metric(
            'ibm_mq.channel.count', expected_value, tags=["channel:my_channel", "status:" + status]
        )


def test_check_regex_tag(aggregator, instance_queue_regex_tag, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_queue_regex_tag)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'mq_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
        'channel:{}'.format(common.CHANNEL),
        'queue:{}'.format(common.QUEUE),
        'foo:bar',
    ]

    for metric, _ in QUEUE_METRICS:
        aggregator.assert_metric(metric, tags=tags)
