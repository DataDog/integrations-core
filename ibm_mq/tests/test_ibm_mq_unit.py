# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.ibm_mq import IbmMqCheck
from datadog_checks.ibm_mq.config import IBMMQConfig

pytestmark = pytest.mark.unit


def test_channel_status_service_check_default_mapping(aggregator, instance):
    # Late import to not require it for e2e
    import pymqi

    check = IbmMqCheck('ibm_mq', {}, [instance])

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
        check._submit_status_check('my_channel', status, ["channel:my_channel_{}".format(status)])

    for status, service_check_status in iteritems(service_check_map):
        aggregator.assert_service_check(
            'ibm_mq.channel.status', service_check_status, tags=["channel:my_channel_{}".format(status)]
        )


def test_channel_status_service_check_custom_mapping(aggregator, instance):
    # Late import to not require it for e2e
    import pymqi

    instance['channel_status_mapping'] = {
        'inactive': 'warning',
        'binding': 'warning',
        'starting': 'warning',
        'running': 'ok',
        'stopping': 'critical',
        'retrying': 'warning',
        'stopped': 'critical',
        'requesting': 'warning',
        'paused': 'warning',
        # 'initializing': '',  # missing mapping are reported as unknown
    }

    check = IbmMqCheck('ibm_mq', {}, [instance])

    service_check_map = {
        pymqi.CMQCFC.MQCHS_INACTIVE: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_BINDING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_STARTING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_RUNNING: AgentCheck.OK,
        pymqi.CMQCFC.MQCHS_STOPPING: AgentCheck.CRITICAL,
        pymqi.CMQCFC.MQCHS_RETRYING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_STOPPED: AgentCheck.CRITICAL,
        pymqi.CMQCFC.MQCHS_REQUESTING: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_PAUSED: AgentCheck.WARNING,
        pymqi.CMQCFC.MQCHS_INITIALIZING: AgentCheck.UNKNOWN,
    }

    for status in service_check_map:
        check._submit_status_check('my_channel', status, ["channel:my_channel_{}".format(status)])

    for status, service_check_status in iteritems(service_check_map):
        aggregator.assert_service_check(
            'ibm_mq.channel.status', service_check_status, tags=["channel:my_channel_{}".format(status)]
        )


@pytest.mark.parametrize('channel_status_mapping', [{'inactive': 'warningXX'}, {'inactiveXX': 'warning'}])
def test_channel_status_service_check_custom_mapping_invalid_config(aggregator, instance, channel_status_mapping):
    instance['channel_status_mapping'] = channel_status_mapping

    with pytest.raises(ConfigurationError):
        IbmMqCheck('ibm_mq', {}, [instance])


@pytest.mark.parametrize(
    'mqcd_version', [pytest.param(10, id='unsupported-version'), pytest.param('foo', id='not-an-int')]
)
def test_invalid_mqcd_version(instance, mqcd_version):
    instance['mqcd_version'] = mqcd_version

    with pytest.raises(ConfigurationError):
        IbmMqCheck('ibm_mq', {}, [instance])


def test_set_mqcd_version(instance):
    import pymqi

    instance['mqcd_version'] = 9
    config = IBMMQConfig(instance)
    assert config.mqcd_version == pymqi.CMQC.MQCD_VERSION_9
