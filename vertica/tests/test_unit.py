# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock

from datadog_checks.vertica import VerticaCheck

CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'certificate')


def test_ssl_config_ok():
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
        'cert': os.path.join(CERTIFICATE_DIR, 'cert.cert'),
        'private_key': os.path.join(CERTIFICATE_DIR, 'server.pem'),
        'ca_cert': CERTIFICATE_DIR,
    }

    check = VerticaCheck('vertica', {}, [instance])

    with mock.patch('datadog_checks.vertica.vertica.vertica') as vertica:
        vertica.connect.return_value = mock.MagicMock()

        check.check(instance)

        assert check._connection is not None
