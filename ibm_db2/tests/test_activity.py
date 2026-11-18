# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta

import pytest

from datadog_checks.base.utils.db.query_metrics import obfuscate_statement
from datadog_checks.ibm_db2.activity import normalize_activity
from datadog_checks.ibm_db2.utils import OBFUSCATION_OPTIONS

pytestmark = pytest.mark.unit


@pytest.fixture
def activity_row() -> dict:
    return {
        'member': 0,
        'application_handle': 41,
        'appl_id': '127.0.0.1.1234.261117000000',
        'uow_id': 2,
        'activity_id': 1,
        'local_start_time': datetime(2026, 11, 17, 23, 59, 59, 987654),
        'observed_timestamp': datetime(2026, 11, 19, 0, 0, 1, 123456),
        'stmt_text': "SELECT TABNAME FROM SYSCAT.TABLES WHERE TABSCHEMA = 'LITERAL_SECRET' /* COMMENT_SECRET */",
        'activity_state': '  EXECUTING  ',
        'session_auth_id': '  DB2APP  ',
        'client_hostname': 'client.example',
        'connection_start_time': datetime(2026, 11, 17, 23),
        'eff_stmt_text': 'RAW_SECRET',
    }


@pytest.fixture(autouse=True)
def obfuscator(monkeypatch: pytest.MonkeyPatch):
    # This is the response shape from the native Agent obfuscator, which the Python stub cannot run.
    monkeypatch.setattr(
        'datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata',
        lambda *_args: {
            'query': 'SELECT TABNAME FROM SYSCAT.TABLES WHERE TABSCHEMA = ?',
            'metadata': {'tables': ['SYSCAT.TABLES'], 'commands': ['SELECT'], 'comments': ['COMMENT_SECRET']},
        },
    )


def test_activity_observation(activity_row: dict):
    """Preserve native execution context and subsecond elapsed time without forwarding raw SQL or comments."""
    result = normalize_activity(activity_row, 'orders', 'instance-a')
    assert result['elapsed_ns'] == 86_401_135_802_000
    assert result['local_start_time'] == '2026-11-17T23:59:59.987654'
    assert result['member'] == 0
    assert result['application_handle'] == 41
    assert result['session_auth_id'] == 'DB2APP'
    assert result['activity_state'] == 'EXECUTING'
    assert result['client_hostname'] == 'client.example'
    assert result['database_name'] == 'orders'
    assert result['dd_tables'] == ['SYSCAT.TABLES']
    assert result['dd_commands'] == ['SELECT']
    assert result['statement'] == 'SELECT TABNAME FROM SYSCAT.TABLES WHERE TABSCHEMA = ?'
    metrics_identity = obfuscate_statement(activity_row['stmt_text'], OBFUSCATION_OPTIONS)
    assert result['query_signature'] == metrics_identity.query_signature == '90a75242b2190030'
    assert 'SECRET' not in json.dumps(result)


def test_activity_identity_survives_polling_and_missing_context(activity_row: dict):
    """Another observation of the same execution keeps its ID even if the optional connection join disappears."""
    first = normalize_activity(activity_row, 'orders', 'instance-a')
    later = {**activity_row, 'observed_timestamp': activity_row['observed_timestamp'] + timedelta(seconds=2)}
    for key in ('session_auth_id', 'client_hostname', 'connection_start_time'):
        later.pop(key)
    second = normalize_activity(later, 'orders', 'instance-a')
    assert second['db_execution_id'] == first['db_execution_id']
    assert second['elapsed_ns'] == first['elapsed_ns'] + 2_000_000_000
    assert not {'session_auth_id', 'client_hostname', 'connection_start_time'} & second.keys()


@pytest.mark.parametrize(
    'column, value',
    [
        ('member', 1),
        ('application_handle', 42),
        ('appl_id', '127.0.0.1.1234.261117000001'),
        ('uow_id', 3),
        ('activity_id', 2),
        ('local_start_time', datetime(2026, 11, 18)),
    ],
)
def test_distinct_executions(activity_row: dict, column: str, value: object):
    """Concurrent sessions and reused native handles must not merge into the same sampled execution."""
    first = normalize_activity(activity_row, 'orders', 'instance-a')
    second = normalize_activity({**activity_row, column: value}, 'orders', 'instance-a')
    assert second['query_signature'] == first['query_signature']
    assert second['db_execution_id'] != first['db_execution_id']


@pytest.mark.parametrize('database, instance', [('other-db', 'instance-a'), ('orders', 'instance-b')])
def test_identity_includes_database(activity_row: dict, database: str, instance: str):
    """Identical native IDs from different monitored databases must not collide."""
    first = normalize_activity(activity_row, 'orders', 'instance-a')
    second = normalize_activity(activity_row, database, instance)
    assert second['db_execution_id'] != first['db_execution_id']


@pytest.mark.parametrize(
    'patch',
    [
        {'stmt_text': None},
        {'stmt_text': '  '},
        {'local_start_time': None},
        {'observed_timestamp': None},
        {'observed_timestamp': datetime(2026, 1, 1)},
        {'application_handle': None},
    ],
)
def test_unusable_observation(activity_row: dict, patch: dict):
    """Unavailable text or identity and invalid time must not fabricate a usable sample."""
    assert normalize_activity({**activity_row, **patch}, 'orders', 'instance-a') is None


def test_obfuscation_failure(activity_row: dict, monkeypatch: pytest.MonkeyPatch):
    """An obfuscator failure must omit the sample instead of sending the original statement."""

    def fail(*_args: object) -> None:
        raise ValueError('Could not obfuscate')

    monkeypatch.setattr('datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata', fail)
    assert normalize_activity(activity_row, 'orders', 'instance-a') is None
