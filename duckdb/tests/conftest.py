# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import duckdb
import pytest

from datadog_checks.dev import WaitFor

from . import common


@pytest.fixture(scope='session')
def connection_db():
    db_file_path = os.path.join(common.HERE, common.DB_NAME)
    connection = duckdb.connect(db_file_path)
    return connection


@pytest.fixture(scope='session')
def dd_environment():
    # yield {"db_name": ":memory:"}
    yield common.DEFAULT_INSTANCE


@pytest.fixture
def instance():
    # return deepcopy({"db_name": ":memory:"})
    return deepcopy(common.DEFAULT_INSTANCE)
