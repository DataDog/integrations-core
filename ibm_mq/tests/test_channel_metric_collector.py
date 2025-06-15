# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from mock import Mock
import pymqi

from datadog_checks.ibm_mq.collectors import ChannelMetricCollector
from datadog_checks.ibm_mq.config import IBMMQConfig

pytestmark = pytest.mark.unit


def test_disable_auto_discover_channels(instance):
    instance['auto_discover_channels'] = False
    del instance['channels']
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()

    collector.get_pcf_channel_metrics(queue_manager)
    collector._submit_channel_status.assert_not_called()


def test_enable_auto_discover_channels(instance):
    instance['auto_discover_channels'] = True
    del instance['channels']
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()

    collector.get_pcf_channel_metrics(queue_manager)
    collector._submit_channel_status.assert_called_once()


def test_channel_metrics(instance):
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()
    # Mock channel info with both regular metrics and connection
    channel_info = {
        pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
        pymqi.CMQCFC.MQCACH_CONNECTION_NAME: b'192.168.1.1(1414)',
        pymqi.CMQCFC.MQIACH_BUFFERS_RCVD: 100,
        pymqi.CMQCFC.MQIACH_BYTES_SENT: 5000,
    }
    collector._discover_channels = Mock(return_value=[channel_info])
    collector.gauge = Mock()
    collector.get_pcf_channel_metrics(queue_manager)
    # Verify regular metrics were submitted
    collector.gauge.assert_any_call(
        'ibm_mq.channel.buffers_rcvd',
        100,
        tags=['channel:TEST.CHANNEL'],
        hostname=None
    )
    collector.gauge.assert_any_call(
        'ibm_mq.channel.bytes_sent',
        5000,
        tags=['channel:TEST.CHANNEL'],
        hostname=None
    )
    # Verify the connection metric was submitted
    collector.gauge.assert_any_call(
        'ibm_mq.channel.conns',
        1,
        tags=['channel:TEST.CHANNEL', 'connection:192.168.1.1(1414)'],
        hostname=None
    )


def test_channel_metrics_no_connection(instance):
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()
    # Mock channel info without connection
    channel_info = {
        pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
        pymqi.CMQCFC.MQIACH_BUFFERS_RCVD: 100,
    }
    collector._discover_channels = Mock(return_value=[channel_info])
    collector.gauge = Mock()
    collector.get_pcf_channel_metrics(queue_manager)
    # Verify regular metrics were submitted
    collector.gauge.assert_any_call(
        'ibm_mq.channel.buffers_rcvd',
        100,
        tags=['channel:TEST.CHANNEL'],
        hostname=None
    )
    # Verify connection metric was not submitted
    for call in collector.gauge.call_args_list:
        assert call[0][0] != 'ibm_mq.channel.conns'


def test_channel_metrics_empty_connection(instance):
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()
    # Mock channel info with empty connection
    channel_info = {
        pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
        pymqi.CMQCFC.MQCACH_CONNECTION_NAME: b'',
        pymqi.CMQCFC.MQIACH_BUFFERS_RCVD: 100,
    }
    collector._discover_channels = Mock(return_value=[channel_info])
    collector.gauge = Mock()
    collector.get_pcf_channel_metrics(queue_manager)
    # Verify regular metrics were submitted
    collector.gauge.assert_any_call(
        'ibm_mq.channel.buffers_rcvd',
        100,
        tags=['channel:TEST.CHANNEL'],
        hostname=None
    )
    # Verify connection metric was not submitted
    for call in collector.gauge.call_args_list:
        assert call[0][0] != 'ibm_mq.channel.conns'


def _get_mocked_instance(instance):
    config = IBMMQConfig(instance, {})
    collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
    collector._discover_channels = Mock(return_value=None)
    collector._submit_channel_status = Mock(return_value=None)
    return collector
