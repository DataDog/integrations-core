# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

INSTANCE = {
    "SILVERSTRIPE_DATABASE_TYPE": "PostgreSQL",
    "SILVERSTRIPE_DATABASE_NAME": "test_db",
    "SILVERSTRIPE_DATABASE_SERVER_IP": "10.10.10.10",
    "SILVERSTRIPE_DATABASE_PORT": 5432,
    "SILVERSTRIPE_DATABASE_USERNAME": "test_user",
    "SILVERSTRIPE_DATABASE_PASSWORD": "test_pass",
    "min_collection_interval": 300,
}


@pytest.fixture(scope="session")
def dd_environment():
    yield


@pytest.fixture
def instance():
    return INSTANCE.copy()
