# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing
from copy import deepcopy

import pytest
from hdbcli.dbapi import Connection as HanaConnection

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.sap_hana.queries import (
    GlobalSystemBackupProgress,
    GlobalSystemConnectionsStatus,
    GlobalSystemDiskUsage,
    GlobalSystemLicenses,
    GlobalSystemRowStoreMemory,
    GlobalSystemServiceComponentMemory,
    GlobalSystemServiceMemory,
    GlobalSystemServiceStatistics,
    GlobalSystemVolumeIO,
    MasterDatabase,
    SystemDatabases,
)

from .common import ADMIN_CONFIG, COMPOSE_FILE, CONFIG, E2E_METADATA, TIMEOUT


class DbManager(object):
    def __init__(self, connection_config, schema):
        self.connection_args = {
            'address': connection_config['server'],
            'port': connection_config['port'],
            'user': connection_config['username'],
            'password': connection_config['password'],
        }
        self.schema = schema
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

                for cls in (MasterDatabase, SystemDatabases):
                    instance = cls()
                    cursor.execute('GRANT SELECT ON {}.{} TO DD_MONITOR'.format(instance.schema, instance.view))

                for cls in (
                    GlobalSystemBackupProgress,
                    GlobalSystemLicenses,
                    GlobalSystemConnectionsStatus,
                    GlobalSystemDiskUsage,
                    GlobalSystemServiceMemory,
                    GlobalSystemServiceComponentMemory,
                    GlobalSystemRowStoreMemory,
                    GlobalSystemServiceStatistics,
                    GlobalSystemVolumeIO,
                ):
                    instance = cls(self.schema)
                    cursor.execute('GRANT SELECT ON {}.{} TO DD_MONITOR'.format(instance.schema, instance.view))

                # For custom query test
                cursor.execute('GRANT SELECT ON {}.M_DATA_VOLUMES TO DD_MONITOR'.format(self.schema))

                # Assign the monitoring role to the user
                cursor.execute('GRANT DD_MONITOR TO datadog')

                # Trigger a backup
                cursor.execute("BACKUP DATA USING FILE ('/tmp/backup')")

    def connect(self):
        self.conn = HanaConnection(**self.connection_args)


@pytest.fixture(scope='session')
def dd_environment(schema="SYS_DATABASES"):
    db = DbManager(ADMIN_CONFIG, schema)

    with docker_run(
        COMPOSE_FILE,
        conditions=[
            CheckDockerLogs(COMPOSE_FILE, ['Startup finished!'], wait=5, attempts=120),
            WaitFor(db.connect),
            db.initialize,
        ],
        env_vars={'PASSWORD': ADMIN_CONFIG['password']},
        sleep=10,
    ):
        yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(CONFIG)


@pytest.fixture
def instance_custom_queries():
    instance = deepcopy(CONFIG)
    instance['custom_queries'] = [
        {
            'tags': ['test:sap_hana'],
            'query': 'SELECT DATABASE_NAME, COUNT(*) FROM SYS_DATABASES.M_DATA_VOLUMES GROUP BY DATABASE_NAME',
            'columns': [{'name': 'db', 'type': 'tag'}, {'name': 'data_volume.total', 'type': 'gauge'}],
            'timeout': TIMEOUT,
        }
    ]
    return instance
