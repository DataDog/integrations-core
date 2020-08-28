# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.log import TRACE_LEVEL
from datadog_checks.vertica import VerticaCheck

CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')


def test_ssl_config_ok(aggregator):
    cert = os.path.join(CERTIFICATE_DIR, 'cert.cert')
    private_key = os.path.join(CERTIFICATE_DIR, 'server.pem')
    instance = {
        'db': 'abc',
        'server': 'localhost',
        'port': '999',
        'username': 'dbadmin',
        'password': 'monitor',
        'timeout': 10,
        'tags': ['foo:bar'],
        'tls_verify': True,
        'validate_hostname': True,
        'cert': cert,
        'private_key': private_key,
        'ca_cert': CERTIFICATE_DIR,
    }

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        with mock.patch('datadog_checks.vertica.vertica.ssl') as ssl:
            vertica.connect.return_value = mock.MagicMock()
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context

            check.check(instance)

            assert tls_context.verify_mode == ssl.CERT_REQUIRED
            assert tls_context.check_hostname is True
            tls_context.load_verify_locations.assert_called_with(None, CERTIFICATE_DIR, None)
            tls_context.load_cert_chain.assert_called_with(cert, keyfile=private_key)

            assert check._connection is not None

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
