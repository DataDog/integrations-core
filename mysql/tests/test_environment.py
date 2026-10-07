# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import configparser
from pathlib import Path

import mock
import pymysql
import pytest

from . import conftest as environment

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'compose_file,start_replication',
    [('mysql-official.yaml', True), ('mysql8.yaml', False), ('mariadb-official.yaml', False), ('percona.yaml', False)],
)
def test_replication_warmup_order(monkeypatch: pytest.MonkeyPatch, compose_file: str, start_replication: bool):
    """The official replica must start after final TCP readiness, before checking its replicated user."""
    events: list[str] = []
    connection = mock.MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = lambda sql: events.append(sql)

    def connect(**kwargs: object) -> mock.MagicMock:
        assert kwargs == {'host': 'localhost', 'port': 13307, 'user': 'root', 'password': 'mypass'}
        events.append('replica TCP ready')
        return connection

    monkeypatch.setattr(environment, 'COMPOSE_FILE', compose_file)
    monkeypatch.setattr(environment, 'MYSQL_REPLICATION', 'classic')
    monkeypatch.setattr(environment.common, 'HOST', 'localhost')
    monkeypatch.setattr(environment.common, 'SLAVE_PORT', 13307)
    monkeypatch.setattr(environment.common, 'mysql_root_password', lambda: 'mypass')
    monkeypatch.setattr(environment.pymysql, 'connect', connect)
    monkeypatch.setattr(environment, 'init_master', lambda: events.append('primary initialized'))
    monkeypatch.setattr(environment, 'init_slave', lambda: events.append('replicated user ready'))
    monkeypatch.setattr(environment, 'CheckDockerLogs', lambda *args: lambda: events.append('replica logs ready'))
    monkeypatch.setattr(environment, 'populate_database', lambda: events.append('populate database'))

    for condition in environment._get_warmup_conditions():
        condition()

    expected = ['primary initialized']
    if start_replication:
        expected.extend(['replica TCP ready', 'START REPLICA;'])
    expected.extend(['replicated user ready', 'replica logs ready', 'populate database'])
    assert events == expected


def test_replication_start_requires_tcp_connection(monkeypatch: pytest.MonkeyPatch):
    """A replica still initializing must leave START REPLICA to the next warmup attempt."""
    connection = mock.MagicMock()
    error = pymysql.err.OperationalError(2003, 'replica TCP not ready')
    connect = mock.MagicMock(return_value=connection, side_effect=error)
    monkeypatch.setattr(environment.pymysql, 'connect', connect)

    with pytest.raises(pymysql.err.OperationalError) as caught:
        environment.init_official_replica()

    assert caught.value is error
    connection.cursor.assert_not_called()


def test_replica_bootstrap_requires_explicit_start():
    """Prevent the bootstrap/shutdown sequence that caused replica SIGSEGV in diagnostic PR #25507."""
    compose_dir = Path(environment.common.HERE) / 'compose'
    config = configparser.ConfigParser()
    config.read(compose_dir / 'mysql-official-replica.conf')
    assert config['mysqld'].getboolean('skip_replica_start')

    sql = (compose_dir / 'mysql_official_replica_initdb' / '01_replication.sql').read_text()
    statements = [
        statement.strip()
        for statement in '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--')).split(';')
        if statement.strip()
    ]
    assert len(statements) == 1
    assert statements[0].startswith('CHANGE REPLICATION SOURCE TO ')
