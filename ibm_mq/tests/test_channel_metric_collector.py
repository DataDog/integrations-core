# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from mock import Mock

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


def _get_mocked_instance(instance):
    config = IBMMQConfig(instance, {})
    collector = ChannelMetricCollector(config, service_check=Mock(), gauge=Mock(), log=Mock())
    collector._discover_channels = Mock(return_value=None)
    collector._submit_channel_status = Mock(return_value=None)
    return collector
