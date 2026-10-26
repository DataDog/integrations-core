# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy
from pathlib import Path

import ibm_db
import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.ibm_db2.connection import get_connection_data

from .common import COMPOSE_FILE, CONFIG, DB2_VERSION, E2E_METADATA


def pytest_ignore_collect(collection_path: Path) -> bool | None:
    # Takeover changes roles; HADR environments collect only that test, even with CI's own -k filter.
    if (
        os.getenv('DB2_HADR') == 'true'
        and collection_path.name.startswith('test_')
        and collection_path.name != 'test_hadr.py'
    ):
        return True
    return None


class DbManager(object):
    def __init__(self, config):
        self.target, self.username, self.password = get_connection_data(
            config['db'],
            config['username'],
            config['password'],
            config['host'],
            config['port'],
            'none',
            None,
            None,
        )
        self.db_name = config['db']
        self.conn = None

    def initialize(self):
        run_command(
            (
                'docker exec ibm_db2 su - db2inst1 -c "db2 -c create db {} using codeset utf-8 territory us"'.format(
                    self.db_name
                )
            ),
            check=True,
        )

        # Enable monitoring
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using HEALTH_MON on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_STMT on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_LOCK on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_TABLE on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_BUFPOOL on"', check=True)

        # Trigger a backup
        # https://www.ibm.com/support/knowledgecenter/en/SSEPGG_11.1.0/com.ibm.db2.luw.admin.cmd.doc/doc/r0001933.html
        run_command(
            (
                'docker exec ibm_db2 su - db2inst1 -c '
                '"db2 -c quiesce instance db2inst1 restricted access immediate force connections"'
            ),
            check=True,
        )
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c deactivate db datadog"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c backup db datadog"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c activate db datadog"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c unquiesce instance db2inst1"', check=True)

    def connect(self):
        ibm_db.close(ibm_db.connect(self.target, self.username, self.password))


@pytest.fixture(scope='session')
def dd_environment():
    db = DbManager(CONFIG)

    # TASKANA ships the instance and logs readiness after db2start; official images create it.
    ready_message = 'Database db2diag log following' if DB2_VERSION == '11.1' else r'\(\*\) Setup has completed\.'
    conditions = [
        CheckDockerLogs(COMPOSE_FILE, ready_message, attempts=60, wait=10),
        db.initialize,
        WaitFor(db.connect),
    ]
    with docker_run(COMPOSE_FILE, conditions=conditions, attempts=2, capture=True):
        yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(CONFIG)
