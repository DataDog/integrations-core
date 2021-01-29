# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

INSTANCE = {
    "user": "testuser",
    "password": "pass",
    "account": "test_acct.us-central1.gcp",
    "database": "SNOWFLAKE",
    "schema": "ACCOUNT_USAGE",
    'role': "ACCOUNTADMIN",
}

OAUTH_INSTANCE = {
    "user": "testuser",
    "account": "test_acct.us-central1.gcp",
    "database": "SNOWFLAKE",
    "schema": "ACCOUNT_USAGE",
    'role': "ACCOUNTADMIN",
    "authenticator": "oauth",
    "token": "testtoken",
}

CHECK_NAME = 'snowflake'


@pytest.fixture(scope='session')
def dd_environment(instance):
    yield instance


@pytest.fixture(scope='session')
def instance():
    return INSTANCE


@pytest.fixture(scope='session')
def oauth_instance():
    return OAUTH_INSTANCE
