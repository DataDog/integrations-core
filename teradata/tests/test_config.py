# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pytest

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.teradata.check import TeradataCheck

from .common import CHECK_NAME, SERVICE_CHECK_CONNECT, SERVICE_CHECK_QUERY


@pytest.mark.parametrize(
    'test_instance, err_msg, is_valid',
    [
        pytest.param(
            {'server': 'localhost', 'username': 'dd_user', 'password': 'db_pass'},
            re.compile(
                'ConfigurationError: Detected 1 error while loading configuration model `InstanceConfig`:'
                '\\n.*(database)\\n.*Field required'
            ),
            False,
            id='Invalid config: missing database',
        ),
        pytest.param(
            {'database': 'main_db', 'username': 'dd_user', 'password': 'db_pass'},
            re.compile(
                'ConfigurationError: Detected 1 error while loading configuration model `InstanceConfig`:\\n.*(server)'
                '\\n.*Field required'
            ),
            False,
            id='Invalid config: missing server',
        ),
        pytest.param(
            {'server': 'localhost', 'database': 'test_db', 'username': 'dd_user', 'password': 'db_pass'},
            '',
            True,
            id='Valid config: Server and database specified',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'JWT'},
            '`auth_data` is required for auth_mechanism: JWT',
            False,
            id='JWT auth: missing auth_data',
        ),
        pytest.param(
            {
                'server': 'tdserver',
                'database': 'db',
                'auth_mechanism': 'JWT',
                'auth_data': 'token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4g'
                'RG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
            },
            '',
            True,
            id='JWT auth: valid config',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'KRB5'},
            '`auth_data` is required for auth_mechanism: KRB5',
            False,
            id='KRB5 auth: missing auth_data',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'TD2'},
            re.compile(
                'Detected 1 error while loading configuration model `InstanceConfig`:\n\n'
                '  Value error, `username` and `password` are required.'
            ),
            False,
            id='TD2 auth: missing username and password',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'TD2', 'username': 'test', 'password': 'test'},
            '',
            True,
            id='TD2 auth: username and password valid',
        ),
        pytest.param(
            {
                'server': 'tdserver',
                'database': 'db',
                'auth_mechanism': 'KRB5',
                'auth_data': 'user1@ESDOM.ESDEV.TDAT@@mypassword',
            },
            '',
            True,
            id='KRB5 auth: valid config',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'LDAP'},
            '`auth_data` is required for auth_mechanism: LDAP',
            False,
            id='LDAP auth: missing auth_data',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'LDAP', 'auth_data': 'username@@userpassword'},
            '',
            True,
            id='LDAP auth: valid config',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'TDNEGO'},
            '',
            True,
            id='TDNEGO auth: no auth_data - valid config',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'auth_mechanism': 'TDNEGO', 'auth_data': 'username@@userpassword'},
            '',
            True,
            id='TDNEGO auth: auth_data - valid config',
        ),
        pytest.param(
            {
                'server': 'tdserver',
                'database': 'db',
                'auth_mechanism': 'TDNEGO',
                'username': 'username',
                'password': 'password',
            },
            '',
            True,
            id='TDNEGO auth: username/pass - valid config',
        ),
        pytest.param(
            {
                'server': 'tdserver',
                'database': 'db',
                'username': 'bob',
                'password': 'pass123',
                'auth_mechanism': 'wrong',
            },
            "Detected 1 error while loading configuration model `InstanceConfig`:\nauth_mechanism\n"
            "  Input should be 'TD2', 'TDNEGO', 'LDAP', 'KRB5' or 'JWT'",
            False,
            id='Auth Mechanism: invalid option',
        ),
        pytest.param(
            {
                'server': 'tdserver',
                'database': 'db',
                'https_port': 433,
                'username': 'username',
                'password': 'userpassword',
            },
            '',
            True,
            id='SSL auth: custom https_port - valid config',
        ),
        pytest.param({'server': 'tdserver', 'database': 'db'}, '', True, id='SSL auth: PREFER - default valid config'),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'ssl_mode': 'Require', 'username': 'bob', 'password': 'pass123'},
            '',
            True,
            id='SSL auth: REQUIRE - valid config',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'ssl_mode': 'Allow', 'username': 'bob', 'password': 'pass123'},
            '',
            True,
            id='SSL auth: ALLOW - valid config',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'ssl_mode': 'Disable', 'username': 'bob', 'password': 'pass123'},
            '',
            True,
            id='SSL auth: DISABLE - valid config',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'ssl_mode': 'WRONG', 'username': 'bob', 'password': 'pass123'},
            "Detected 1 error while loading configuration model `InstanceConfig`:\nssl_mode\n"
            "  Input should be 'Allow', 'Disable', 'Prefer' or 'Require'",
            False,
            id='SSL auth: invalid mode',
        ),
        pytest.param(
            {'server': 'tdserver', 'database': 'db', 'ssl_mode': 'VERIFY-CA', 'username': 'bob', 'password': 'pass123'},
            "Detected 1 error while loading configuration model `InstanceConfig`:\nssl_mode\n"
            "  Input should be 'Allow', 'Disable', 'Prefer' or 'Require'",
            False,
            id='SSL auth: invalid unsupported mode',
        ),
    ],
)
def test_config(dd_run_check, aggregator, test_instance, err_msg, is_valid):
    check = TeradataCheck(CHECK_NAME, {}, [test_instance])
    conn = mock.MagicMock()
    cursor = conn.cursor()
    cursor.rowcount = float('+inf')

    teradatasql = mock.MagicMock()
    teradatasql.connect.return_value = conn

    mocks = [
        ('datadog_checks.teradata.check.teradatasql', teradatasql),
        ('datadog_checks.teradata.check.TERADATASQL_IMPORT_ERROR', None),
    ]

    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))

        if not is_valid:
            with pytest.raises(
                Exception,
                match=err_msg,
            ):
                dd_run_check(check)
        else:
            try:
                dd_run_check(check)
                aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, count=1)
                aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.OK, count=1)
            except AssertionError as e:
                raise AssertionError(e)
