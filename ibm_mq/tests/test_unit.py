# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pymqi
from six import iteritems

from datadog_checks.ibm_mq import IbmMqCheck, constants
from datadog_checks.ibm_mq.config import Config


def test_check_channel_count(aggregator, instance_queue_regex_tag):
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


def test_check_channel_count_status_unknown(aggregator, instance_queue_regex_tag):
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


def test__discover_queues():
    check = IbmMqCheck('ibm_mq', {}, {})

    pcf_conn = mock.MagicMock()
    pcf_conn.MQCMD_INQUIRE_Q.return_value = [
        {pymqi.CMQC.MQCA_Q_NAME: 'MY.QUEUE.PREDEFINED1', pymqi.CMQC.MQIA_DEFINITION_TYPE: pymqi.CMQC.MQQDT_PREDEFINED},
        {
            pymqi.CMQC.MQCA_Q_NAME: 'MY.QUEUE.PERMANENT_DYNAMIC',
            pymqi.CMQC.MQIA_DEFINITION_TYPE: pymqi.CMQC.MQQDT_PERMANENT_DYNAMIC,
        },
        {
            pymqi.CMQC.MQCA_Q_NAME: 'MY.QUEUE.TEMPORARY_DYNAMIC',
            pymqi.CMQC.MQIA_DEFINITION_TYPE: pymqi.CMQC.MQQDT_TEMPORARY_DYNAMIC,
        },
        {
            pymqi.CMQC.MQCA_Q_NAME: 'MY.QUEUE.SHARED_DYNAMIC',
            pymqi.CMQC.MQIA_DEFINITION_TYPE: pymqi.CMQC.MQQDT_SHARED_DYNAMIC,
        },
        {pymqi.CMQC.MQCA_Q_NAME: 'MY.QUEUE.PREDEFINED2', pymqi.CMQC.MQIA_DEFINITION_TYPE: pymqi.CMQC.MQQDT_PREDEFINED},
    ]

    config = Config({'queue_definition_types': ['PREDEFINED', 'TEMPORARY_DYNAMIC']})
    queues = check._discover_queues_from_mq_pattern(config, pcf_conn, 'dummy')

    assert set(queues) == {'MY.QUEUE.PREDEFINED1', 'MY.QUEUE.PREDEFINED2', 'MY.QUEUE.TEMPORARY_DYNAMIC'}

    config = Config({'queue_definition_types': []})
    queues = check._discover_queues_from_mq_pattern(config, pcf_conn, 'dummy')
    assert set(queues) == {
        'MY.QUEUE.PREDEFINED1',
        'MY.QUEUE.PREDEFINED2',
        'MY.QUEUE.TEMPORARY_DYNAMIC',
        'MY.QUEUE.SHARED_DYNAMIC',
        'MY.QUEUE.PERMANENT_DYNAMIC',
    }


def test__submit_channel_stats(aggregator):
    check = IbmMqCheck('ibm_mq', {}, {})

    config = mock.MagicMock()
    config.channels = ['MY.CHANNEL']  # Deprecated, declared here but should NOT be propagated

    pcf_conn = mock.MagicMock()
    pcf_conn.MQCMD_INQUIRE_CHANNEL.return_value = [
        {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'MY.CHANNEL.1',
            pymqi.CMQCFC.MQIACH_BATCH_SIZE: 10,
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: 1,
        }
    ]

    pcf_conn.MQCMD_INQUIRE_CHANNEL_STATUS.return_value = [
        {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'MY.CHANNEL.2',
            pymqi.CMQCFC.MQIACH_BUFFERS_RCVD: 3,
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: 1,
        }
    ]

    check._submit_channel_stats(config, pcf_conn, ['my:tag'])

    aggregator.assert_metric('ibm_mq.channel.batch_size', 10, tags=['my:tag', 'channel:MY.CHANNEL.1'])
    aggregator.assert_metric('ibm_mq.channel.buffers_rcvd', 3, tags=['my:tag', 'channel:MY.CHANNEL.2'])


def test__submit_metric_by_type(aggregator):
    check = IbmMqCheck('ibm_mq', {}, {})

    check._submit_metric_by_type(constants.GAUGE, "my.metric1", 10, ['my:tag1'])
    check._submit_metric_by_type(constants.RATE, "my.metric2", 20, ['my:tag2'])
    check._submit_metric_by_type("unknown", "my.metric3", 30, ['my:tag3'])

    aggregator.assert_metric("my.metric1", 10, metric_type=aggregator.GAUGE, tags=['my:tag1'])
    aggregator.assert_metric("my.metric2", 20, metric_type=aggregator.RATE, tags=['my:tag2'])
