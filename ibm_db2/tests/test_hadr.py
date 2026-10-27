# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Real takeover against a disposable pair provisioned by the Linux HADR matrix.

Run `ddev --no-interactive test ibm_db2:py3.13-12.1.5.0-hadr` (or another matrix
version). The fixture uses direct container IPs and disables IBM client reroute.
The separate environment keeps the role swap away from ordinary write tests.
"""

import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from time import sleep
from uuid import uuid4
from xml.etree import ElementTree

import ibm_db
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.structures import EnvVars
from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.connection import Db2Connection
from datadog_checks.ibm_db2.query_metrics import QueryMetricsCollector

HADR_COMPOSE_FILE = str(Path(__file__).parent / 'docker' / 'docker-compose-hadr.yaml')
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != 'linux', reason='HADR tests use direct container IPs on Linux'),
    pytest.mark.skipif(os.getenv('DB2_HADR') != 'true', reason='Runs in the dedicated HADR matrix environments'),
]


def _compose(*args: str) -> str:
    return subprocess.check_output(
        ['docker', 'compose', '-f', HADR_COMPOSE_FILE, *args], stderr=subprocess.STDOUT, text=True, timeout=600
    ).strip()


def _db2(service: str, command: str) -> str:
    return _compose('exec', '-T', service, 'su', '-', 'db2inst1', '-c', command)


def _initialize_hadr() -> None:
    for service in ('primary', 'standby'):
        _db2(service, 'db2set DB2_HADR_ROS=ON && db2stop force && db2start')
    # Both containers share only the backup, not their database storage.
    _compose('exec', '-T', 'primary', 'chown', 'db2inst1:db2iadm1', '/hadr')
    _db2('primary', 'db2 create db datadog using codeset utf-8 territory us')
    _db2('primary', 'mkdir -p /tmp/hadr-archive')
    _db2('standby', 'mkdir -p /tmp/hadr-archive')
    _db2(
        'primary',
        'db2 update db cfg for datadog using LOGARCHMETH1 DISK:/tmp/hadr-archive '
        'MON_ACT_METRICS BASE MON_REQ_METRICS BASE LOGINDEXBUILD ON '
        'HADR_LOCAL_HOST primary HADR_LOCAL_SVC 55000 HADR_REMOTE_HOST standby '
        'HADR_REMOTE_SVC 55000 HADR_REMOTE_INST db2inst1 HADR_SYNCMODE SYNC HADR_TIMEOUT 30',
    )
    _db2('primary', 'db2 backup db datadog to /hadr')
    _db2('standby', 'db2 restore db datadog from /hadr without prompting')
    _db2('standby', 'db2 update db cfg for datadog using HADR_LOCAL_HOST standby HADR_REMOTE_HOST primary')
    _db2('standby', 'db2 start hadr on db datadog as standby')
    _db2('primary', 'db2 start hadr on db datadog as primary')


def _hadr_ready() -> bool:
    return all(
        re.search(r'HADR_STATE\s*=\s*PEER', _db2(service, 'db2pd -db datadog -hadr'))
        for service in ('primary', 'standby')
    )


@pytest.fixture(scope='module')
def hadr_hosts(tmp_path_factory: pytest.TempPathFactory) -> Iterator[list[str]]:
    conditions = [
        CheckDockerLogs(HADR_COMPOSE_FILE, r'\(\*\) Setup has completed\.', service=service, attempts=60, wait=10)
        for service in ('primary', 'standby')
    ]
    conditions.extend([_initialize_hadr, WaitFor(_hadr_ready, attempts=60, wait=2)])
    with docker_run(
        HADR_COMPOSE_FILE,
        conditions=conditions,
        capture=True,
        env_vars={'COMPOSE_PROJECT_NAME': f'ibm-db2-hadr-{uuid4().hex[:8]}'},
    ):
        hosts = []
        for service in ('primary', 'standby'):
            container = _compose('ps', '-q', service)
            info = json.loads(subprocess.check_output(['docker', 'inspect', container], text=True))[0]
            hosts.append(next(iter(info['NetworkSettings']['Networks'].values()))['IPAddress'])

        for service, alternate in zip(('primary', 'standby'), reversed(hosts)):
            _db2(
                service,
                f'db2 update alternate server for database datadog using hostname {alternate} port 50000 '
                '&& db2 terminate',
            )

        config = ElementTree.Element('configuration')
        databases = ElementTree.SubElement(config, 'databases')
        for host, alternate in zip(hosts, reversed(hosts)):
            database = ElementTree.SubElement(databases, 'database', name='datadog', host=host, port='50000')
            # Connection-level balancing can change targets even when ACR is disabled.
            ElementTree.SubElement(database, 'parameter', name='connectionLevelLoadBalancing', value='false')
            acr = ElementTree.SubElement(database, 'acr')
            for name in ('enableAcr', 'enableAlternateServerListFirstConnect'):
                ElementTree.SubElement(acr, 'parameter', name=name, value='false')
            alternates = ElementTree.SubElement(acr, 'alternateserverlist')
            for name, target in (('configured', host), ('alternate', alternate)):
                ElementTree.SubElement(alternates, 'server', name=name, hostname=target, port='50000')
        ElementTree.indent(config)
        driver_path = tmp_path_factory.mktemp('db2-driver')
        ElementTree.ElementTree(config).write(driver_path / 'db2dsdriver.cfg', encoding='utf-8')
        with EnvVars({'DB2DSDRIVER_CFG_PATH': str(driver_path)}):
            yield hosts


def test_fixed_server_takeover(instance: dict, aggregator: AggregatorStub, hadr_hosts: list[str]):
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
        checks = [IbmDb2Check('ibm_db2', {}, [{**instance, 'dbm': True, 'host': h, 'port': 50000}]) for h in hadr_hosts]
        jobs = [check._query_metrics for check in checks]
        connections = [Db2Connection(check, check._config) for check in checks]
        for job, connection in zip(jobs, connections):
            cleanup.callback(job.shutdown)
            cleanup.callback(connection.close)
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
        _db2('standby', 'db2 takeover hadr on db datadog')
        for job in jobs:
            for attempt in range(30):
                try:
                    count = collect(job)
                    break
                except AssertionError:
                    raise
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
