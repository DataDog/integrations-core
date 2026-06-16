# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import ibm_db
import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.ibm_db2 import IbmDb2Check

from .common import COMPOSE_FILE, CONFIG, DB2_IMAGE, DBM_PASSWORD, DBM_USERNAME, E2E_METADATA


class DbManager(object):
    def __init__(self, config):
        self.target, self.username, self.password = IbmDb2Check.get_connection_data(
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
        if DB2_IMAGE != 'icr.io/db2_community/db2':
            run_command(
                (
                    'docker exec ibm_db2 su - db2inst1 -c '
                    '"db2 -x \\"connect to {}\\" >/dev/null 2>&1 || '
                    'db2 \\"create db {} using codeset utf-8 territory us\\""'.format(self.db_name, self.db_name)
                ),
                check=True,
            )
        WaitFor(self.connect, attempts=120, wait=5)()

        # Enable monitoring
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using HEALTH_MON on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_STMT on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_LOCK on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_TABLE on"', check=True)
        run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c update dbm cfg using DFT_MON_BUFPOOL on"', check=True)
        run_command(
            'docker exec ibm_db2 su - db2inst1 -c "db2 -c update db cfg for datadog using MON_ACT_METRICS BASE"',
            check=True,
        )
        run_command(
            'docker exec ibm_db2 su - db2inst1 -c "db2 -c update db cfg for datadog using MON_REQ_METRICS BASE"',
            check=True,
        )
        run_command(
            'docker exec ibm_db2 su - db2inst1 -c "db2 -c update db cfg for datadog using MON_OBJ_METRICS EXTENDED"',
            check=True,
        )
        self.create_dbm_user()
        WaitFor(self.grant_dbm_privileges, attempts=120, wait=5)()

        if DB2_IMAGE != 'icr.io/db2_community/db2':
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

    def create_dbm_user(self):
        run_command(
            (
                "docker exec ibm_db2 bash -c "
                "\"id -u {username} >/dev/null 2>&1 || useradd -m -s /bin/bash {username}; "
                "echo '{username}:{password}' | chpasswd\""
            ).format(username=DBM_USERNAME, password=DBM_PASSWORD),
            check=True,
        )

    def grant_dbm_privileges(self):
        connection = ibm_db.connect(self.target, self.username, self.password)
        try:
            _execute_ignoring_duplicate(
                connection, 'CREATE SCHEMA {} AUTHORIZATION {}'.format(DBM_USERNAME, DBM_USERNAME)
            )
            _execute_ignoring_duplicate(
                connection,
                "CALL SYSPROC.SYSINSTALLOBJECTS('EXPLAIN', 'C', NULL, '{}')".format(DBM_USERNAME.upper()),
            )
            ibm_db.exec_immediate(connection, 'GRANT CONNECT ON DATABASE TO USER {}'.format(DBM_USERNAME))
            ibm_db.exec_immediate(
                connection,
                'GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT TO USER {}'.format(DBM_USERNAME),
            )
            ibm_db.exec_immediate(
                connection,
                'GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_ACTIVITY TO USER {}'.format(DBM_USERNAME),
            )
            ibm_db.exec_immediate(
                connection,
                'GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_CONNECTION TO USER {}'.format(DBM_USERNAME),
            )
            ibm_db.exec_immediate(
                connection,
                'GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_UNIT_OF_WORK TO USER {}'.format(DBM_USERNAME),
            )
            ibm_db.exec_immediate(
                connection,
                'GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_APPLICATION_HANDLE TO USER {}'.format(DBM_USERNAME),
            )
            ibm_db.exec_immediate(
                connection,
                'GRANT EXECUTE ON PROCEDURE SYSPROC.EXPLAIN_FROM_SECTION TO USER {}'.format(DBM_USERNAME),
            )
            ibm_db.exec_immediate(
                connection,
                'GRANT EXECUTE ON PROCEDURE SYSPROC.SYSINSTALLOBJECTS TO USER {}'.format(DBM_USERNAME),
            )
            for table_name in _get_schema_tables(connection, DBM_USERNAME):
                ibm_db.exec_immediate(
                    connection,
                    'GRANT SELECT, INSERT, DELETE ON TABLE {}.{} TO USER {}'.format(
                        DBM_USERNAME, table_name, DBM_USERNAME
                    ),
                )
            ibm_db.exec_immediate(connection, 'GRANT SELECT ON TABLE SYSIBMADM.DBMCFG TO USER {}'.format(DBM_USERNAME))
            ibm_db.exec_immediate(connection, 'GRANT SELECT ON TABLE SYSIBMADM.DBCFG TO USER {}'.format(DBM_USERNAME))
        finally:
            ibm_db.close(connection)


@pytest.fixture(scope='session')
def dd_environment():
    db = DbManager(CONFIG)

    with docker_run(COMPOSE_FILE, conditions=[db.initialize, WaitFor(db.connect)], attempts=2):
        yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(CONFIG)


@pytest.fixture
def dbm_instance(instance):
    instance['username'] = DBM_USERNAME
    instance['password'] = DBM_PASSWORD
    instance['dbm'] = True
    instance['query_metrics'] = {'run_sync': True, 'collection_interval': 0.1}
    instance['database_identifier'] = {'template': '$resolved_hostname:$db'}
    return instance


def _execute_ignoring_duplicate(connection, query):
    try:
        ibm_db.exec_immediate(connection, query)
    except Exception as e:
        if 'SQLSTATE=42710' not in str(e):
            raise


def _get_schema_tables(connection, schema_name):
    statement = ibm_db.exec_immediate(
        connection,
        "SELECT TABNAME FROM SYSCAT.TABLES WHERE TABSCHEMA = '{}' AND TYPE = 'T'".format(schema_name.upper()),
    )
    table_names = []
    row = ibm_db.fetch_assoc(statement)
    while row:
        table_names.append(row['TABNAME'])
        row = ibm_db.fetch_assoc(statement)
    return table_names
