# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os

import mock
import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.log import TRACE_LEVEL
from datadog_checks.vertica import VerticaCheck
from datadog_checks.vertica.utils import parse_major_version

CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')
cert = os.path.join(CERTIFICATE_DIR, 'cert.cert')
private_key = os.path.join(CERTIFICATE_DIR, 'server.pem')


def test_ssl_config_ok(aggregator, tls_instance):
    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
            vertica.connect.return_value = mock.MagicMock()
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context
            check = VerticaCheck('vertica', {}, [tls_instance])
            check.check(tls_instance)

            assert check._client.use_tls
            assert tls_context.verify_mode == ssl.CERT_REQUIRED
            assert tls_context.check_hostname is True
            tls_context.load_verify_locations.assert_called_with(cadata=None, cafile=None, capath=CERTIFICATE_DIR)
            tls_context.load_cert_chain.assert_called_with(cert, keyfile=private_key, password=None)

    aggregator.assert_service_check("vertica.can_connect", status=AgentCheck.OK, tags=['db:abc', 'foo:bar'])


def test_ssl_legacy_config_ok(aggregator, tls_instance_legacy):
    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
            vertica.connect.return_value = mock.MagicMock()
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context
            check = VerticaCheck('vertica', {}, [tls_instance_legacy])
            check.check(tls_instance_legacy)

            assert check._client.use_tls
            assert tls_context.verify_mode == ssl.CERT_REQUIRED
            assert tls_context.check_hostname is True
            tls_context.load_verify_locations.assert_called_with(cadata=None, cafile=None, capath=CERTIFICATE_DIR)
            tls_context.load_cert_chain.assert_called_with(cert, keyfile=private_key, password=None)

    aggregator.assert_service_check("vertica.can_connect", status=AgentCheck.OK, tags=['db:abc', 'foo:bar'])


def test_client_logging_enabled(aggregator, instance):
    instance['client_lib_log_level'] = 'DEBUG'

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
            log_level='DEBUG',
            log_path='',
        )


def test_client_logging_disabled(aggregator, instance):
    instance['client_lib_log_level'] = None
    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
        )


@pytest.mark.parametrize(
    'agent_log_level, expected_vertica_log_level', [(logging.DEBUG, logging.DEBUG), (TRACE_LEVEL, logging.DEBUG)]
)
def test_client_logging_enabled_debug_if_agent_uses_debug_or_trace(
    aggregator, instance, agent_log_level, expected_vertica_log_level
):
    """
    Improve collection of debug flares by automatically enabling client DEBUG logs when the Agent uses DEBUG logs.
    """
    instance.pop('client_lib_log_level', None)
    root_logger = logging.getLogger()
    root_logger.setLevel(agent_log_level)

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
            log_level=expected_vertica_log_level,
            log_path='',
        )


def test_client_logging_disabled_if_agent_uses_info(aggregator, instance):
    """
    Library logs should be disabled by default, in particular under normal Agent operation (INFO level).
    """
    instance.pop('client_lib_log_level', None)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        check.check(instance)

        vertica.connect.assert_called_with(
            database=mock.ANY,
            host=mock.ANY,
            port=mock.ANY,
            user=mock.ANY,
            password=mock.ANY,
            backup_server_node=mock.ANY,
            connection_load_balance=mock.ANY,
            connection_timeout=mock.ANY,
        )


def test_connection_error_service_check(aggregator, instance, monkeypatch):
    check = VerticaCheck('vertica', {}, [instance])

    monkeypatch.setattr(check._client, 'connect', mock.Mock(side_effect=Exception))

    check.check(instance)

    aggregator.assert_service_check("vertica.can_connect", status=AgentCheck.CRITICAL, tags=['db:datadog', 'foo:bar'])


def test_invalid_groups_in_config(instance):
    instance['metric_groups'] = ['system', 'a_group_that_does_not_exist']

    with pytest.raises(ConfigurationError):
        VerticaCheck('vertica', {}, [instance]).parse_metric_groups()


@pytest.mark.parametrize(
    'version_string, expected',
    [
        ('Vertica Analytic Database v11.1.1-0', '11.1.1+0'),
        ('Vertica Analytic Database v10.0.0-1', '10.0.0+1'),
    ],
)
def test_VerticaCheck_parse_db_version(version_string, expected):
    assert VerticaCheck.parse_db_version(version_string) == expected


@pytest.mark.parametrize('version_string, expected', [('v9.2.0-7', 9), ('v11.1.1-0', 11)])
def test_parse_major_version(version_string, expected):
    assert parse_major_version(version_string) == expected
