# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Opt-in takeover test against a disposable, readable-standby Db2 pair.

Set DB2_HADR_PRIMARY_HOST, DB2_HADR_STANDBY_HOST, and DB2_HADR_STANDBY_CONTAINER.
Both servers use the integration's test credentials and port 50000. Configure the
IBM driver with ACR disabled as in the README. The test swaps the servers' roles.
Run it separately from the ordinary suite, which needs a writable primary:
`ddev --no-interactive test ibm_db2:py3.13-12.1.5.0 -- tests/test_hadr.py`.
Select the matrix environment matching both servers' version (11.1.4.7, 11.5.5.1, or 12.1.5.0).
"""

import os
import subprocess
from contextlib import ExitStack
from time import sleep
from uuid import uuid4

import ibm_db
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.connection import Db2Connection
from datadog_checks.ibm_db2.query_metrics import QueryMetricsCollector

from .common import DB2_VERSION

HADR_HOSTS = (os.getenv('DB2_HADR_PRIMARY_HOST'), os.getenv('DB2_HADR_STANDBY_HOST'))
STANDBY_CONTAINER = os.getenv('DB2_HADR_STANDBY_CONTAINER')
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not all((*HADR_HOSTS, STANDBY_CONTAINER)), reason='Requires a disposable Db2 HADR pair'),
]


def test_fixed_server_takeover(instance: dict, aggregator: AggregatorStub):
    """Each server emits only its own executions, with stable identity across reconnect and takeover."""
    table = f'DBM_HADR_{uuid4().hex.upper()}'
    query = f'SELECT ID FROM {table} WHERE ID > 1 WITH UR'

    def execute(connection: Db2Connection, sql: str) -> list[tuple]:
        cursor = ibm_db.exec_immediate(connection.ensure_connected(), sql)
        try:
            rows = []
            if ibm_db.num_fields(cursor):
                while (row := ibm_db.fetch_tuple(cursor)) is not False:
                    rows.append(row)
            return rows
        finally:
            ibm_db.free_stmt(cursor)

    def collect(job: QueryMetricsCollector) -> int:
        aggregator.reset()
        job.run_job()
        payloads = aggregator.get_event_platform_events('dbm-metrics')
        for payload in payloads:
            assert payload['database_instance'] == job._check.database_identifier
            assert payload['host'] == job._check.reported_hostname
        return sum(
            row['count']
            for payload in payloads
            for row in payload['ibm_db2_rows']
            if table.lower() in row['query'].lower()
        )

    with ExitStack() as cleanup:
        checks = [IbmDb2Check('ibm_db2', {}, [{**instance, 'dbm': True, 'host': h, 'port': 50000}]) for h in HADR_HOSTS]
        jobs = [check._query_metrics for check in checks]
        connections = [Db2Connection(check, check._config) for check in checks]
        for job, connection in zip(jobs, connections):
            cleanup.callback(job.shutdown)
            cleanup.callback(connection.close)
            major, minor = DB2_VERSION.split('.')[:2]
            assert ibm_db.server_info(connection.ensure_connected()).DBMS_VER.startswith(
                f'{int(major):02}.{int(minor):02}.'
            )
        identities = [check.database_identifier for check in checks]
        assert len(set(identities)) == 2
        host_query = 'SELECT HOST_NAME FROM SYSIBMADM.ENV_SYS_INFO'
        servers = [execute(conn, host_query) for conn in connections]
        primary, standby = connections
        execute(primary, f'CREATE TABLE {table} (ID INTEGER)')
        execute(primary, f'INSERT INTO {table} VALUES (1), (2), (3)')
        # DDL replay can briefly interrupt readable-standby connections.
        for attempt in range(30):
            try:
                execute(standby, query)
                break
            except Exception:
                if attempt == 29:
                    raise
                sleep(1)
        execute(primary, query)
        assert [collect(job) for job in jobs] == [0, 0]
        for connection, count in zip(connections, (3, 5)):
            for _ in range(count):
                execute(connection, query)
        assert [collect(job) for job in jobs] == [3, 5]
        for connection, job in zip(connections, jobs):
            for _ in range(2):
                execute(connection, query)
            job._connection.close()
        assert [collect(job) for job in jobs] == [2, 2]
        for connection in connections:
            connection.close()
        subprocess.run(
            ['docker', 'exec', STANDBY_CONTAINER, 'su', '-', 'db2inst1', '-c', 'db2 takeover hadr on db datadog'],
            check=True,
            timeout=120,
        )
        for job in jobs:
            for attempt in range(30):
                try:
                    count = collect(job)
                    break
                except Exception:
                    if attempt == 29:
                        raise
                    sleep(1)
            assert count == 0
        assert [execute(conn, host_query) for conn in connections] == servers
        for connection in connections:
            execute(connection, query)
        for job in jobs:
            collect(job)
        for connection, count in zip(connections, (7, 11)):
            for _ in range(count):
                execute(connection, query)
        assert [collect(job) for job in jobs] == [7, 11]
        assert [check.database_identifier for check in checks] == identities
        assert [collect(job) for job in jobs] == [0, 0]
        primary.close()
        for job in jobs:
            job.shutdown()
        execute(standby, f'DROP TABLE {table}')
