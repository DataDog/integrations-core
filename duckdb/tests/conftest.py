# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import os
from copy import deepcopy

import duckdb
from datadog_checks.dev import WaitFor, docker_run

from . import common

def container_up(service_name, port):
    """
    Try to connect to duckdb
    """
    duckdb.connect(
        host=common.HOST, port=common.port, database=common.DB, read_only=False
    )

@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')

    with docker_run(compose_file, conditions=[
        WaitFor(container_up, args=("DuckDB", common.PORT)),
        ]):
        yield common.DEFAULT_INSTANCE


@pytest.fixture
def instance():
    return deepcopy(common.DEFAULT_INSTANCE)