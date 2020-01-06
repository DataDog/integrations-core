# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock

from datadog_checks.base import AgentCheck
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
