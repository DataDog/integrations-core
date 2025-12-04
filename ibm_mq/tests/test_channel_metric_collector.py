# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pymqi
import pytest
from mock import Mock, patch

from datadog_checks.ibm_mq.collectors import ChannelMetricCollector
from datadog_checks.ibm_mq.config import IBMMQConfig

pytestmark = pytest.mark.unit

# Common test data
EXPECTED_BASE_TAGS = [
    'queue_manager:QM1',
    'connection_name:localhost(11414)',
    'foo:bar',
    'mq_host:localhost',
    'port:11414',
]

EXPECTED_CHANNEL_TAGS = EXPECTED_BASE_TAGS + ['channel:TEST.CHANNEL']


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


@pytest.mark.parametrize(
    'channel_info,expected_metrics',
    [
        # Basic channel metrics
        (
            {
                pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
                pymqi.CMQCFC.MQIACH_BATCH_SIZE: 100,
                pymqi.CMQCFC.MQIACH_BATCH_INTERVAL: 5000,
            },
            [
                ('ibm_mq.channel.batch_size', 100),
                ('ibm_mq.channel.batch_interval', 5000),
            ],
        ),
        # Channel without connection
        (
            {
                pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
                pymqi.CMQCFC.MQIACH_BATCH_SIZE: 100,
            },
            [('ibm_mq.channel.batch_size', 100)],
        ),
        # Channel with empty connection
        (
            {
                pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
                pymqi.CMQCFC.MQCACH_CONNECTION_NAME: b'',
                pymqi.CMQCFC.MQIACH_BATCH_SIZE: 100,
            },
            [('ibm_mq.channel.batch_size', 100)],
        ),
    ],
)
def test_channel_metrics_variations(instance, channel_info, expected_metrics):
    """Test channel metrics collection with various channel configurations."""
    collector = _get_mocked_instance(instance)
    queue_manager = Mock()
    collector._discover_channels = Mock(return_value=[channel_info])
    collector.gauge = Mock()
    collector.get_pcf_channel_metrics(queue_manager)

    # Verify expected metrics were submitted
    for metric_name, expected_value in expected_metrics:
        collector.gauge.assert_any_call(
            metric_name,
            expected_value,
            tags=EXPECTED_CHANNEL_TAGS,
            hostname=None,
        )


def test_channel_status_metrics(instance):
    """Test channel status metrics collection including connection metrics."""
    with patch('datadog_checks.ibm_mq.collectors.channel_metric_collector.pymqi.PCFExecute') as mock_pcf:
        channel_info = {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
            pymqi.CMQCFC.MQCACH_CONNECTION_NAME: b'192.168.1.1(1414)',
            pymqi.CMQCFC.MQIACH_BUFFERS_RCVD: 100,
            pymqi.CMQCFC.MQIACH_BYTES_SENT: 5000,
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: 3,
        }
        mock_pcf_instance = Mock()
        mock_pcf_instance.MQCMD_INQUIRE_CHANNEL_STATUS.return_value = [channel_info]
        mock_pcf.return_value = mock_pcf_instance

        config = IBMMQConfig(instance, {})
        collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
        queue_manager = Mock()
        collector._submit_channel_status(queue_manager, 'TEST.CHANNEL', config.tags_no_channel)

        # Verify status metrics were submitted
        collector.gauge.assert_any_call(
            'ibm_mq.channel.buffers_rcvd',
            100,
            tags=EXPECTED_CHANNEL_TAGS,
            hostname=None,
        )
        collector.gauge.assert_any_call(
            'ibm_mq.channel.bytes_sent',
            5000,
            tags=EXPECTED_CHANNEL_TAGS,
            hostname=None,
        )
        # Verify the connection metric was submitted (default behavior)
        collector.gauge.assert_any_call(
            'ibm_mq.channel.conn_status',
            1,
            tags=EXPECTED_CHANNEL_TAGS + ['connection:192.168.1.1(1414)'],
            hostname=None,
        )


def test_connections_active_metric(instance):
    """Test connections_active metric calculation."""
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
            channel_info_running_1,
            channel_info_running_2,
            channel_info_stopped,
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
            tags=EXPECTED_CHANNEL_TAGS,
            hostname=None,
        )


@pytest.mark.parametrize(
    'collect_connection_metrics,should_collect_conn_status',
    [
        (True, True),
        (False, False),
    ],
)
def test_collect_connection_metrics_config_option(instance, collect_connection_metrics, should_collect_conn_status):
    """Test that collect_connection_metrics configuration option properly controls conn_status metric collection."""
    instance['collect_connection_metrics'] = collect_connection_metrics

    with patch('datadog_checks.ibm_mq.collectors.channel_metric_collector.pymqi.PCFExecute') as mock_pcf:
        channel_info = {
            pymqi.CMQCFC.MQCACH_CHANNEL_NAME: b'TEST.CHANNEL',
            pymqi.CMQCFC.MQCACH_CONNECTION_NAME: b'192.168.1.1(1414)',
            pymqi.CMQCFC.MQIACH_CHANNEL_STATUS: 3,
        }
        mock_pcf_instance = Mock()
        mock_pcf_instance.MQCMD_INQUIRE_CHANNEL_STATUS.return_value = [channel_info]
        mock_pcf.return_value = mock_pcf_instance

        config = IBMMQConfig(instance, {})
        collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
        queue_manager = Mock()
        collector._submit_channel_status(queue_manager, 'TEST.CHANNEL', config.tags_no_channel)

        if should_collect_conn_status:
            # Verify the connection metric was submitted when enabled
            collector.gauge.assert_any_call(
                'ibm_mq.channel.conn_status',
                1,
                tags=EXPECTED_CHANNEL_TAGS + ['connection:192.168.1.1(1414)'],
                hostname=None,
            )
        else:
            # Verify the connection metric was NOT submitted when disabled
            for call in collector.gauge.call_args_list:
                metric_name = call[0][0] if call[0] else None
                assert metric_name != 'ibm_mq.channel.conn_status', (
                    "conn_status metric should not be collected when collect_connection_metrics is False"
                )


def _get_mocked_instance(instance):
    config = IBMMQConfig(instance, {})
    collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
    collector._discover_channels = Mock(return_value=None)
    collector._submit_channel_status = Mock(return_value=None)
    return collector
