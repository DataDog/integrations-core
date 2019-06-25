# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import pymqi
import pytest
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.ibm_mq import IbmMqCheck

from . import common

log = logging.getLogger(__file__)


@pytest.mark.usefixtures("dd_environment")
def test_service_check_connection_issues(aggregator, instance, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'mq_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
    ]

    channel_tags = tags + ['channel:{}'.format(common.CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.OK, tags=channel_tags)

    bad_channel_tags = tags + ['channel:{}'.format(common.BAD_CHANNEL)]
    aggregator.assert_service_check('ibm_mq.channel', check.CRITICAL, tags=bad_channel_tags)


@pytest.mark.usefixtures("dd_environment")
def test__submit_channel_status_check(aggregator, instance, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})

    service_check_map = {
        pymqi.CMQCFC.MQCHS_INACTIVE: AgentCheck.CRITICAL,
        pymqi.CMQCFC.MQCHS_BINDING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_STARTING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_RUNNING: AgentCheck.OK,
        pymqi.CMQCFC.MQCHS_STOPPING: AgentCheck.CRITICAL,
        pymqi.CMQCFC.MQCHS_RETRYING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_STOPPED: AgentCheck.CRITICAL,
        pymqi.CMQCFC.MQCHS_REQUESTING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_PAUSED: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_INITIALIZING: AgentCheck.WARNING,
    }

    for status in service_check_map:
        check._submit_channel_status_check('my_channel', status, ["channel:my_channel_{}".format(status)])

    for status, service_check_status in iteritems(service_check_map):
        aggregator.assert_service_check(
            'ibm_mq.channel.status', service_check_status, tags=["channel:my_channel_{}".format(status)]
        )


@pytest.mark.usefixtures("dd_environment")
def test_check_queue_pattern(aggregator, instance_queue_pattern, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_queue_pattern)

    for metric in common.EXPECTED_METRICS_ALL:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_check_queue_regex(aggregator, instance_queue_regex, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_queue_regex)

    for metric in common.EXPECTED_METRICS_ALL:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_check_all(aggregator, instance_collect_all, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_collect_all)

    for metric in common.EXPECTED_METRICS_ALL:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

    for service_check in common.EXPECTED_SERVICE_CHECKS:
        aggregator.assert_service_check(service_check)


@pytest.mark.usefixtures("dd_environment")
def test_channel_tags(aggregator, instance_collect_all, seed_data):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_collect_all)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'mq_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
    ]

    aggregator.assert_metric('ibm_mq.channel.alteration_datetime', tags=tags + ['channel:DEV.ADMIN.SVRCONN'])
    aggregator.assert_metric('ibm_mq.channel.alteration_datetime', tags=tags + ['channel:DEV.APP.SVRCONN'])
    aggregator.assert_metric('ibm_mq.channel.alteration_datetime', count=0, tags=tags + ['channel:*'])


@pytest.mark.usefixtures("dd_environment")
def test_check_regex_tag(aggregator, instance_queue_regex_tag):
    check = IbmMqCheck('ibm_mq', {}, {})
    check.check(instance_queue_regex_tag)

    tags = [
        'queue_manager:{}'.format(common.QUEUE_MANAGER),
        'mq_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
        'queue:{}'.format(common.QUEUE),
        'channel:{}'.format(common.CHANNEL),
        'foo:bar',
    ]

    for metric in common.EXPECTED_QUEUE_METRICS:
        aggregator.assert_metric(metric, tags=tags)
