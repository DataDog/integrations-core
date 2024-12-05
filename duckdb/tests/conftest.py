# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import os
from copy import deepcopy

import duckdb
from datadog_checks.dev import LazyFunction, docker_run

from . import common

class InitializeDB(LazyFunction):
    def __init__(self, config):
        self.conn_info = common.connection_options_from_config(config)

    def __call__(self):
        with duckdb.connect(**self.conn_info) as conn:
            cur = conn.cursor()

@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')

    with docker_run(compose_file, log_patterns=['Duckdb is now running'], conditions=[InitializeDB(common.CONFIG)]):
        yield common.CONFIG


@pytest.fixture
def instance():
    return deepcopy(common.CONFIG)