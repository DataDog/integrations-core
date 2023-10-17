# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

CHECK_NAME = 'snowflake'
INSTANCE = {
    'username': 'testuser',
    'password': 'pass',
    'account': 'test_acct.us-central1.gcp',
    'database': 'SNOWFLAKE',
    'schema': 'ACCOUNT_USAGE',
    'role': 'ACCOUNTADMIN',
    'disable_generic_tags': True,
    'login_timeout': 3,
    'aggregate_last_24_hours': True,
}

OAUTH_INSTANCE = {
    'username': 'testuser',
    'account': 'test_acct.us-central1.gcp',
    'database': 'SNOWFLAKE',
    'schema': 'ACCOUNT_USAGE',
    'role': 'ACCOUNTADMIN',
    'authenticator': 'oauth',
    'token': 'testtoken',
    'disable_generic_tags': True,
    'login_timeout': 3,
}

EXPECTED_TAGS = ['account:test_acct.us-central1.gcp']
E2E_METADATA = {
    'post_install_commands': [
        # Need new version of pip to upgrade setuptools...
        'pip install --upgrade pip',
        # Agent ships old version of setuptools which for some reason leads to errors during loading:
        #   File "/opt/datadog-agent/embedded/lib/python3.8/site-packages/snowflake/connector/options.py", line 11, ...
        #     import pkg_resources
        # ModuleNotFoundError: No module named 'pkg_resources'
        'pip install --upgrade setuptools',
        'pip install /home/snowflake_connector_patch',
    ],
    'docker_volumes': [
        '{}:/home/snowflake_connector_patch'.format(os.path.join(HERE, 'snowflake_connector_patch')),
        '{}:/home/keys'.format(os.path.join(HERE, 'keys')),
    ],
}
