# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pymqi
import pytest
from mock import Mock, patch

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
    # Mock channel info with configuration metrics
    channel_info = {
        pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
        pymqi.CMQCFC.MQIACH_BATCH_SIZE: 100,
        pymqi.CMQCFC.MQIACH_BATCH_INTERVAL: 5000,
    }
    collector._discover_channels = Mock(return_value=[channel_info])
    collector.gauge = Mock()
    collector.get_pcf_channel_metrics(queue_manager)
    # Verify configuration metrics were submitted
    collector.gauge.assert_any_call(
        'ibm_mq.channel.batch_size',
        100,
        tags=[
            'queue_manager:QM1',
            'connection_name:localhost(11414)',
            'foo:bar',
            'mq_host:localhost',
            'port:11414',
            'channel:TEST.CHANNEL',
        ],
        hostname=None,
    )
    collector.gauge.assert_any_call(
        'ibm_mq.channel.batch_interval',
        5000,
        tags=[
            'queue_manager:QM1',
            'connection_name:localhost(11414)',
            'foo:bar',
            'mq_host:localhost',
            'port:11414',
            'channel:TEST.CHANNEL',
        ],
        hostname=None,
    )


def test_channel_metrics_no_connection(instance):
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()
    # Mock channel info without connection
    channel_info = {
        pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
        pymqi.CMQCFC.MQIACH_BATCH_SIZE: 100,
    }
    collector._discover_channels = Mock(return_value=[channel_info])
    collector.gauge = Mock()
    collector.get_pcf_channel_metrics(queue_manager)
    # Verify configuration metrics were submitted
    collector.gauge.assert_any_call(
        'ibm_mq.channel.batch_size',
        100,
        tags=[
            'queue_manager:QM1',
            'connection_name:localhost(11414)',
            'foo:bar',
            'mq_host:localhost',
            'port:11414',
            'channel:TEST.CHANNEL',
        ],
        hostname=None,
    )


def test_channel_metrics_empty_connection(instance):
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()
    # Mock channel info with empty connection
    channel_info = {
        pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
        pymqi.CMQCFC.MQCACH_CONNECTION_NAME: b'',
        pymqi.CMQCFC.MQIACH_BATCH_SIZE: 100,
    }
    collector._discover_channels = Mock(return_value=[channel_info])
    collector.gauge = Mock()
    collector.get_pcf_channel_metrics(queue_manager)
    # Verify configuration metrics were submitted
    collector.gauge.assert_any_call(
        'ibm_mq.channel.batch_size',
        100,
        tags=[
            'queue_manager:QM1',
            'connection_name:localhost(11414)',
            'foo:bar',
            'mq_host:localhost',
            'port:11414',
            'channel:TEST.CHANNEL',
        ],
        hostname=None,
    )


def test_channel_status_metrics(instance):
    # Patch pymqi.PCFExecute before creating the collector
    with patch('datadog_checks.ibm_mq.collectors.channel_metric_collector.pymqi.PCFExecute') as mock_pcf:
        # Mock channel info with all required status metrics fields
        channel_info = {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
            pymqi.CMQCFC.MQCACH_CONNECTION_NAME: b'192.168.1.1(1414)',
            pymqi.CMQCFC.MQIACH_BUFFERS_RCVD: 100,
            pymqi.CMQCFC.MQIACH_BYTES_SENT: 5000,
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: 3,  # Add a valid status value
        }
        mock_pcf_instance = Mock()
        mock_pcf_instance.MQCMD_INQUIRE_CHANNEL_STATUS.return_value = [channel_info]
        mock_pcf.return_value = mock_pcf_instance
        # Instantiate ChannelMetricCollector directly
        config = IBMMQConfig(instance, {})
        collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
        queue_manager = Mock()
        collector._submit_channel_status(queue_manager, 'TEST.CHANNEL', config.tags_no_channel)
        # Verify status metrics were submitted
        collector.gauge.assert_any_call(
            'ibm_mq.channel.buffers_rcvd',
            100,
            tags=[
                'queue_manager:QM1',
                'connection_name:localhost(11414)',
                'foo:bar',
                'mq_host:localhost',
                'port:11414',
                'channel:TEST.CHANNEL',
            ],
            hostname=None,
        )
        collector.gauge.assert_any_call(
            'ibm_mq.channel.bytes_sent',
            5000,
            tags=[
                'queue_manager:QM1',
                'connection_name:localhost(11414)',
                'foo:bar',
                'mq_host:localhost',
                'port:11414',
                'channel:TEST.CHANNEL',
            ],
            hostname=None,
        )
        # Verify the connection metric was submitted
        collector.gauge.assert_any_call(
            'ibm_mq.channel.conn_status',
            1,
            tags=[
                'queue_manager:QM1',
                'connection_name:localhost(11414)',
                'foo:bar',
                'mq_host:localhost',
                'port:11414',
                'channel:TEST.CHANNEL',
                'connection:192.168.1.1(1414)',
            ],
            hostname=None,
        )


def test_connections_active_metric(instance):
    # Patch pymqi.PCFExecute before creating the collector
    with patch('datadog_checks.ibm_mq.collectors.channel_metric_collector.pymqi.PCFExecute') as mock_pcf:
        # Mock two running channel instances and one stopped
        channel_info_running_1 = {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: pymqi.CMQCFC.MQCHS_RUNNING,
        }
        channel_info_running_2 = {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: pymqi.CMQCFC.MQCHS_RUNNING,
        }
        channel_info_stopped = {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: pymqi.CMQCFC.MQCHS_STOPPED,
        }
        mock_pcf_instance = Mock()
        mock_pcf_instance.MQCMD_INQUIRE_CHANNEL_STATUS.return_value = [
            channel_info_running_1, channel_info_running_2, channel_info_stopped
        ]
        mock_pcf.return_value = mock_pcf_instance
        config = IBMMQConfig(instance, {})
        collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
        queue_manager = Mock()
        collector._submit_channel_status(queue_manager, 'TEST.CHANNEL', config.tags_no_channel)
        # Should submit connections_active = 2
        collector.gauge.assert_any_call(
            'ibm_mq.channel.connections_active',
            2,
            tags=[
                'queue_manager:QM1',
                'connection_name:localhost(11414)',
                'foo:bar',
                'mq_host:localhost',
                'port:11414',
                'channel:TEST.CHANNEL',
            ],
            hostname=None,
        )


def _get_mocked_instance(instance):
    config = IBMMQConfig(instance, {})
    collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
    collector._discover_channels = Mock(return_value=None)
    collector._submit_channel_status = Mock(return_value=None)
    return collector
