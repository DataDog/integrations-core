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


@pytest.mark.parametrize(
    'instance_config, expected_connection_name',
    [
        pytest.param({}, 'localhost(1414)', id='empty'),
        pytest.param({'host': 'foo'}, 'foo(1414)', id='only host'),
        pytest.param({'port': '1234'}, 'localhost(1234)', id='only port'),
        pytest.param({'host': 'foo', 'port': 3333}, 'foo(3333)', id='host port'),
        pytest.param({'connection_name': 'baz(8888)'}, 'baz(8888)', id='connection_name'),
    ],
)
def test_connection_config_ok(instance_config, expected_connection_name):
    instance_config.update({'channel': 'foo', 'queue_manager': 'bar'})

    config = IBMMQConfig(instance_config)

    assert config.connection_name == expected_connection_name


@pytest.mark.parametrize(
    'instance_config',
    [pytest.param({'host': 'localhost', 'port': 1000, 'connection_name': 'localhost(1234)'}, id='both')],
)
def test_connection_config_error(instance_config):
    instance_config.update({'channel': 'foo', 'queue_manager': 'bar'})

    with pytest.raises(ConfigurationError) as excinfo:
        IBMMQConfig(instance_config)

    assert 'Specify only one host/port or connection_name configuration' in str(excinfo.value)


@pytest.mark.parametrize(
    'instance_config',
    [
        pytest.param({'channel': 'foo'}, id='channel and default queue manager'),
        pytest.param({'channel': 'foo', 'queue_manager': 'abc'}, id='both'),
    ],
)
def test_channel_queue_config_ok(instance_config):
    instance_config.update({'host': 'localhost', 'port': 1000})

    IBMMQConfig(instance_config)
    # finish without configuration error


@pytest.mark.parametrize(
    'instance_config',
    [
        pytest.param({}, id='empty'),
        pytest.param({'channel': 'foo', 'queue_manager': ''}, id='empty queue manager'),
        pytest.param({'channel': '', 'queue_manager': 'abc'}, id='empty channel'),
        pytest.param({'channel': '', 'queue_manager': ''}, id='both empty'),
    ],
)
def test_channel_queue_config_error(instance_config):
    instance_config.update({'host': 'localhost', 'port': 1000})

    with pytest.raises(ConfigurationError) as excinfo:
        IBMMQConfig(instance_config)

    assert 'channel, queue_manager are required configurations' in str(excinfo.value)
