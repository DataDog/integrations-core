# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import pytest

from datadog_checks.ibm_mq import IbmMqCheck

from . import common

log = logging.getLogger(__file__)

METRICS = [
    'ibm_mq.queue.service_interval',
    'ibm_mq.queue.inhibit_put',
    'ibm_mq.queue.depth_low_limit',
    'ibm_mq.queue.inhibit_get',
    'ibm_mq.queue.harden_get_backout',
    'ibm_mq.queue.service_interval_event',
    'ibm_mq.queue.trigger_control',
    'ibm_mq.queue.usage',
    'ibm_mq.queue.scope',
    'ibm_mq.queue.type',
    'ibm_mq.queue.depth_max',
    'ibm_mq.queue.backout_threshold',
    'ibm_mq.queue.depth_high_event',
    'ibm_mq.queue.depth_low_event',
    'ibm_mq.queue.trigger_message_priority',
    'ibm_mq.queue.depth_current',
    'ibm_mq.queue.depth_max_event',
    'ibm_mq.queue.open_input_count',
    'ibm_mq.queue.persistence',
    'ibm_mq.queue.trigger_depth',
    'ibm_mq.queue.max_message_length',
    'ibm_mq.queue.depth_high_limit',
    'ibm_mq.queue.priority',
    'ibm_mq.queue.input_open_option',
    'ibm_mq.queue.message_delivery_sequence',
    'ibm_mq.queue.retention_interval',
    'ibm_mq.queue.open_output_count',
    'ibm_mq.queue.trigger_type',
    'ibm_mq.queue.depth_percent',
    'ibm_mq.queue_manager.dist_lists',
    'ibm_mq.queue_manager.max_msg_list',
    'ibm_mq.channel.channels',
]

OPTIONAL_METRICS = [
    'ibm_mq.queue.max_channels',
    'ibm_mq.channel.batch_size',
    'ibm_mq.channel.batch_interval',
    'ibm_mq.channel.long_retry_count',
    'ibm_mq.channel.long_retry_interval',
    'ibm_mq.channel.max_message_length',
    'ibm_mq.channel.short_retry_count',
]


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, instance, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()

    tags = ['queue_manager:datadog', 'host:localhost', 'port:11414']

    channel_tags = tags + ['channel:{}'.format(common.CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.OK, tags=channel_tags)
    bad_channel_tags = tags + ['channel:{}'.format(common.BAD_CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.CRITICAL, tags=bad_channel_tags)


@pytest.mark.usefixtures("dd_environment")
def test_check_pattern(aggregator, instance_pattern, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_pattern)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_check_all(aggregator, instance_collect_all, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_collect_all)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
