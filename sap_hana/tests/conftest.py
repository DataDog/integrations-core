# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing
from copy import deepcopy

import pyhdb
import pytest

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.sap_hana.queries import Query

from .common import ADMIN_CONFIG, COMPOSE_FILE, CONFIG, E2E_METADATA


class DbManager(object):
    def __init__(self, config):
        self.connection_args = {
            'host': config['server'],
            'port': config['port'],
            'user': config['username'],
            'password': config['password'],
        }
        self.conn = None

    def initialize(self):
        with closing(self.conn) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute('CREATE RESTRICTED USER datadog PASSWORD "{}"'.format(CONFIG['password']))
                cursor.execute('ALTER USER datadog ENABLE CLIENT CONNECT')
                cursor.execute('ALTER USER datadog DISABLE PASSWORD LIFETIME')

                # Create a role with the necessary monitoring privileges
                cursor.execute('CREATE ROLE DD_MONITOR')
                cursor.execute('GRANT CATALOG READ TO DD_MONITOR')
                for cls in Query.__subclasses__():
                    for view in cls.views:
                        cursor.execute('GRANT SELECT ON {} TO DD_MONITOR'.format(view))

                # For custom query test
                cursor.execute('GRANT SELECT ON SYS_DATABASES.M_DATA_VOLUMES TO DD_MONITOR')

                # Assign the monitoring role to the user
                cursor.execute('GRANT DD_MONITOR TO datadog')

                # Trigger a backup
                cursor.execute("BACKUP DATA USING FILE ('/tmp/backup')")

    def connect(self):
        import logging; logging.warning("Attempt connection")
        self.conn = pyhdb.connect(**self.connection_args)


@pytest.fixture(scope='session')
def dd_environment():
    db = DbManager(ADMIN_CONFIG)

    with docker_run(
        COMPOSE_FILE,
        conditions=[
            # CheckDockerLogs(COMPOSE_FILE, ['Startup finished!'], wait=5, attempts=120),
            WaitFor(db.connect),
            db.initialize,
        ],
        env_vars={'PASSWORD': ADMIN_CONFIG['password']},
    ):
        yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(CONFIG)
