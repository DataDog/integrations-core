# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest
import vertica_python as vertica

from datadog_checks.dev import LazyFunction, docker_run

from . import common
from .db import setup_db_tables  # noqa: F401


class InitializeDB(LazyFunction):
    def __init__(self, config):
        self.conn_info = common.connection_options_from_config(config)

    def __call__(self):
        with vertica.connect(**self.conn_info) as conn:
            cur = conn.cursor()

            # Create data
            cur.execute('CREATE TABLE {} (a INT, b VARCHAR(32))'.format(common.ID))
            cur.execute("INSERT INTO {} (a, b) VALUES (9000, 'DBZ')".format(common.ID))
            conn.commit()

            # Trigger an audit
            cur.execute('SELECT AUDIT_LICENSE_SIZE()')

            # Enable load balance policy
            # https://docs.vertica.com/12.0.x/en/admin/managing-client-connections/connection-load-balancing/
            cur.execute("SELECT SET_LOAD_BALANCE_POLICY('ROUNDROBIN')")


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')

    with docker_run(compose_file, log_patterns=['Vertica is now running'], conditions=[InitializeDB(common.CONFIG)]):
        yield common.CONFIG


@pytest.fixture
def instance():
    return deepcopy(common.CONFIG)


@pytest.fixture
def tls_instance():
    return deepcopy(common.TLS_CONFIG)


@pytest.fixture
def tls_instance_legacy():
    return deepcopy(common.TLS_CONFIG_LEGACY)
