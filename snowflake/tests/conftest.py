# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common

INSTANCE = {
    "user": "testuser",
    "password": "pass",
    "account": "test_acct.us-central1.gcp",
    "database": "SNOWFLAKE",
    "schema": "ACCOUNT_USAGE",
    'role': "ACCOUNTADMIN",
    'disable_generic_tags': True,
}

OAUTH_INSTANCE = {
    "user": "testuser",
    "account": "test_acct.us-central1.gcp",
    "database": "SNOWFLAKE",
    "schema": "ACCOUNT_USAGE",
    'role': "ACCOUNTADMIN",
    "authenticator": "oauth",
    "token": "testtoken",
    'disable_generic_tags': True,
}


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE, common.E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


@pytest.fixture
def oauth_instance():
    return deepcopy(common.OAUTH_INSTANCE)
