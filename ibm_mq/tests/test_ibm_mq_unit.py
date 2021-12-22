# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError

from .common import skip_windows_ci

pytestmark = pytest.mark.unit


def test_channel_status_service_check_default_mapping(aggregator, get_check, instance):
    # Late import to not require it for e2e
    import pymqi

    check = get_check(instance)

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
        check.channel_metric_collector._submit_status_check(
            'my_channel', status, ["channel:my_channel_{}".format(status)]
        )

    for status, service_check_status in iteritems(service_check_map):
        aggregator.assert_service_check(
            'ibm_mq.channel.status', service_check_status, tags=["channel:my_channel_{}".format(status)]
        )


def test_channel_status_service_check_custom_mapping(aggregator, get_check, instance):
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

    check = get_check(instance)

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
        check.channel_metric_collector._submit_status_check(
            'my_channel', status, ["channel:my_channel_{}".format(status)]
        )

    for status, service_check_status in iteritems(service_check_map):
        aggregator.assert_service_check(
            'ibm_mq.channel.status', service_check_status, tags=["channel:my_channel_{}".format(status)]
        )


@pytest.mark.parametrize('channel_status_mapping', [{'inactive': 'warningXX'}, {'inactiveXX': 'warning'}])
def test_channel_status_service_check_custom_mapping_invalid_config(get_check, instance, channel_status_mapping):
    instance['channel_status_mapping'] = channel_status_mapping

    with pytest.raises(ConfigurationError):
        get_check(instance)


@pytest.mark.parametrize(
    'mqcd_version', [pytest.param(10, id='unsupported-version'), pytest.param('foo', id='not-an-int')]
)
def test_invalid_mqcd_version(get_check, instance, mqcd_version):
    instance['mqcd_version'] = mqcd_version

    with pytest.raises(ConfigurationError):
        get_check(instance)


def test_set_mqcd_version(instance):
    import pymqi

    from datadog_checks.ibm_mq.config import IBMMQConfig

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
    from datadog_checks.ibm_mq.config import IBMMQConfig

    instance_config.update({'channel': 'foo', 'queue_manager': 'bar'})

    config = IBMMQConfig(instance_config)

    assert config.connection_name == expected_connection_name


@pytest.mark.parametrize(
    'instance_config',
    [pytest.param({'host': 'localhost', 'port': 1000, 'connection_name': 'localhost(1234)'}, id='both')],
)
def test_connection_config_error(instance_config):
    from datadog_checks.ibm_mq.config import IBMMQConfig

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
    from datadog_checks.ibm_mq.config import IBMMQConfig

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
    from datadog_checks.ibm_mq.config import IBMMQConfig

    instance_config.update({'host': 'localhost', 'port': 1000})

    with pytest.raises(ConfigurationError) as excinfo:
        IBMMQConfig(instance_config)

    assert 'channel, queue_manager are required configurations' in str(excinfo.value)


@skip_windows_ci
def test_ssl_connection_creation(get_check, instance):
    """
    Test that we are not getting unicode/bytes type error.
    """
    # Late import to not require it for e2e
    import pymqi

    instance['ssl_auth'] = 'yes'
    instance['ssl_cipher_spec'] = 'TLS_RSA_WITH_AES_256_CBC_SHA256'
    instance['ssl_key_repository_location'] = '/dummy'

    check = get_check(instance)

    with pytest.raises(pymqi.MQMIError) as excinfo:
        check.check(instance)

    assert excinfo.value.reason == pymqi.CMQC.MQRC_KEY_REPOSITORY_ERROR

    assert len(check.warnings) == 1
    warning = check.warnings[0]

    # Check that we are not getting a unicode/bytes type error but a MQRC_KEY_REPOSITORY_ERROR (dummy location)
    assert 'bytes' not in warning
    assert 'unicode' not in warning
    assert 'MQRC_KEY_REPOSITORY_ERROR' in warning


def test_ssl_check_normal_connection_before_ssl_connection(instance_ssl_dummy):
    import logging

    import pymqi

    from datadog_checks.ibm_mq.config import IBMMQConfig
    from datadog_checks.ibm_mq.connection import get_queue_manager_connection

    logger = logging.getLogger(__file__)
    config = IBMMQConfig(instance_ssl_dummy)

    error = pymqi.MQMIError(pymqi.CMQC.MQCC_FAILED, pymqi.CMQC.MQRC_UNKNOWN_CHANNEL_NAME)
    with mock.patch(
        'datadog_checks.ibm_mq.connection.get_normal_connection', side_effect=error
    ) as get_normal_connection, mock.patch('datadog_checks.ibm_mq.connection.get_ssl_connection') as get_ssl_connection:

        with pytest.raises(pymqi.MQMIError):
            get_queue_manager_connection(config, logger)

        get_normal_connection.assert_called_with(config, logger)
        assert not get_ssl_connection.called

    # normal connection failed with with error other those listed in get_queue_manager_connection
    for error_reason in [pymqi.CMQC.MQRC_HOST_NOT_AVAILABLE, pymqi.CMQC.MQRC_SSL_CONFIG_ERROR]:
        error = pymqi.MQMIError(pymqi.CMQC.MQCC_FAILED, error_reason)
        with mock.patch(
            'datadog_checks.ibm_mq.connection.get_normal_connection', side_effect=error
        ) as get_normal_connection, mock.patch(
            'datadog_checks.ibm_mq.connection.get_ssl_connection'
        ) as get_ssl_connection:

            get_queue_manager_connection(config, logger)

            get_normal_connection.assert_called_with(config, logger)
            get_ssl_connection.assert_called_with(config, logger)

    # no issue with normal connection
    with mock.patch('datadog_checks.ibm_mq.connection.get_normal_connection') as get_normal_connection, mock.patch(
        'datadog_checks.ibm_mq.connection.get_ssl_connection'
    ) as get_ssl_connection:

        get_queue_manager_connection(config, logger)

        get_normal_connection.assert_called_with(config, logger)
        get_ssl_connection.assert_called_with(config, logger)
