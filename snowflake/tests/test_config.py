# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.snowflake import SnowflakeCheck

from .common import CHECK_NAME


@pytest.mark.parametrize(
    'options',
    [
        pytest.param({}, id='default'),
        pytest.param({'token': 'mytoken'}, id='wrong parameters'),
        pytest.param({'authenticator': 'unknown'}, id='wrong authenticator'),
        pytest.param({'password': 'pass', 'private_key_password': 'pass'}, id='missing private_key_path'),
        pytest.param(
            {
                'only_custom_queries': True,
                'username': 'test',
                'password': 'test',
                'metric_groups': ['snowflake.billing'],
            },
            id='incompatible options',
        ),
    ],
)
def test_authenticator_option_fail(options):
    instance = {
        # Common configuration
        'account': 'test_acct.us-central1.gcp',
        'database': 'SNOWFLAKE',
        'schema': 'ACCOUNT_USAGE',
        'role': 'ACCOUNTADMIN',
        'user': 'testuser',
    }

    instance.update(options)

    with pytest.raises(ConfigurationError):
        check = SnowflakeCheck(CHECK_NAME, {}, [instance])
        check.load_configuration_models()


@pytest.mark.parametrize(
    'options',
    [
        pytest.param({'password': 'pass'}, id='password'),
        pytest.param({'authenticator': 'snowflake_jwt', 'private_key_path': '/path/to/key'}, id='key pair auth'),
        pytest.param({'authenticator': 'oauth', 'token_path': '/path/to/token'}, id='token path'),
        pytest.param({'authenticator': 'oauth', 'token': 'mytoken'}, id='token'),
        pytest.param(
            {
                'only_custom_queries': True,
                'username': 'test',
                'password': 'test',
                'metric_groups': [],
                'custom_queries': [{}],
            },
            id='valid only_custom_queries',
        ),
    ],
)
def test_authenticator_option_pass(options):
    instance = {
        # Common configuration
        'account': 'test_acct.us-central1.gcp',
        'database': 'SNOWFLAKE',
        'schema': 'ACCOUNT_USAGE',
        'role': 'ACCOUNTADMIN',
        'username': 'testuser',
    }
    instance.update(options)

    check = SnowflakeCheck(CHECK_NAME, {}, [instance])
    check.load_configuration_models()
