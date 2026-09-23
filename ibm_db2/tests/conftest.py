# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import ibm_db
import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.ibm_db2.connection import get_connection_data

from .common import COMPOSE_FILE, CONFIG, E2E_METADATA

SCHEMA_OBJECTS = (
    "CREATE TABLE TEST_SCHEMA.PARENT (ID INT NOT NULL PRIMARY KEY, NAME VARCHAR(50) NOT NULL DEFAULT 'x', "
    "PRICE DECIMAL(10,2))",
    "CREATE TABLE TEST_SCHEMA.CHILD (ID INT NOT NULL PRIMARY KEY, PARENT_ID INT, "
    "CONSTRAINT FK_PARENT FOREIGN KEY (PARENT_ID) REFERENCES TEST_SCHEMA.PARENT (ID) ON DELETE CASCADE)",
    "CREATE INDEX TEST_SCHEMA.IDX_CHILD_PARENT ON TEST_SCHEMA.CHILD (PARENT_ID DESC)",
    "CREATE TABLE TEST_SCHEMA.EVENTS (ID INT NOT NULL, TS DATE NOT NULL) "
    "PARTITION BY RANGE (TS) (STARTING '2026-01-01' ENDING '2026-12-31' EVERY 6 MONTHS)",
    "CREATE SCHEMA EMPTY_SCHEMA",
)


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

    def create_schema_objects(self):
        conn = ibm_db.connect(self.target, self.username, self.password)
        try:
            for statement in SCHEMA_OBJECTS:
                ibm_db.exec_immediate(conn, statement)
        finally:
            ibm_db.close(conn)


@pytest.fixture(scope='session')
def dd_environment():
    db = DbManager(CONFIG)

    # The official image creates the Db2 instance at container start, which takes a few minutes.
    setup_complete = CheckDockerLogs(COMPOSE_FILE, 'Setup has completed', attempts=60, wait=10)
    with docker_run(
        COMPOSE_FILE,
        conditions=[setup_complete, db.initialize, WaitFor(db.connect), db.create_schema_objects],
        attempts=2,
    ):
        yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(CONFIG)
