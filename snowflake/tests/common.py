# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

CHECK_NAME = 'snowflake'
INSTANCE = {
    'user': 'testuser',
    'password': 'pass',
    'account': 'test_acct.us-central1.gcp',
    'database': 'SNOWFLAKE',
    'schema': 'ACCOUNT_USAGE',
    'role': 'ACCOUNTADMIN',
}
OAUTH_INSTANCE = {
    'user': 'testuser',
    'account': 'test_acct.us-central1.gcp',
    'database': 'SNOWFLAKE',
    'schema': 'ACCOUNT_USAGE',
    'role': 'ACCOUNTADMIN',
    'authenticator': 'oauth',
    'token': 'testtoken',
}

EXPECTED_TAGS = ['account:test_acct.us-central1.gcp']
E2E_METADATA = {
    'post_install_commands': ['pip install /home/mock_snowflake_connector_python'],
    'docker_volumes': [
        '{}:/home/mock_snowflake_connector_python'.format(os.path.join(HERE, 'mock_snowflake_connector_python'))
    ],
}
