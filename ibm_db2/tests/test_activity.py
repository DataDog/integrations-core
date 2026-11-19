# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta

import pytest

from datadog_checks.ibm_db2.activity import IDENTITY_COLUMNS, normalize_activity

pytestmark = pytest.mark.unit


@pytest.fixture
def activity_row() -> dict:
    return {
        'member': 0,
        'application_handle': 41,
        'appl_id': '127.0.0.1.1234.261117000000',
        'uow_id': 2,
        'activity_id': 1,
        'executable_id': b'\x00\xab\xff',
        'planid': 42,
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
    """Preserve execution context, extracted comments, and elapsed time without forwarding raw SQL."""
    result = normalize_activity(activity_row, 'orders')
    assert result['elapsed_ns'] == 86_401_135_802_000
    assert result['local_start_time'] == '2026-11-17T23:59:59.987654'
    assert {key: result[key] for key in IDENTITY_COLUMNS} == {
        'member': 0,
        'application_handle': 41,
        'appl_id': '127.0.0.1.1234.261117000000',
        'uow_id': 2,
        'activity_id': 1,
    }
    assert result['session_auth_id'] == 'DB2APP'
    assert result['activity_state'] == 'EXECUTING'
    assert result['client_hostname'] == 'client.example'
    assert result['database_name'] == 'orders'
    assert result['dd_tables'] == ['SYSCAT.TABLES']
    assert result['dd_commands'] == ['SELECT']
    assert result['dd_comments'] == ['COMMENT_SECRET']
    assert result['query_truncated'] == 'not_truncated'
    assert result['executable_id'] == '00abff'
    assert result['planid'] == 42
    assert result['statement'] == 'SELECT TABNAME FROM SYSCAT.TABLES WHERE TABSCHEMA = ?'
    assert result['query_signature'] == '90a75242b2190030'
    assert 'LITERAL_SECRET' not in json.dumps(result)
    assert 'RAW_SECRET' not in json.dumps(result)
    assert 'eff_stmt_text' not in result


@pytest.mark.parametrize('text_bytes, expected', [(16_384, 'not_truncated'), (16_385, 'truncated')])
def test_activity_truncation(activity_row: dict, text_bytes: int, expected: str):
    """Identify incomplete SQL from the reader's original byte count, including the exact limit."""
    result = normalize_activity({**activity_row, 'stmt_text_bytes': text_bytes}, 'orders')
    assert result['query_truncated'] == expected


@pytest.mark.parametrize('missing', [None, 'absent'])
def test_activity_optional_identifiers(activity_row: dict, missing: str | None):
    """Unavailable package-cache identity must not discard an otherwise usable activity observation."""
    for key in ('executable_id', 'planid'):
        if missing is None:
            activity_row[key] = None
        else:
            activity_row.pop(key)
    result = normalize_activity(activity_row, 'orders')
    assert result is not None
    assert not {'executable_id', 'planid'} & result.keys()


def test_activity_elapsed_survives_missing_context(activity_row: dict):
    """Elapsed time advances even if the optional connection join disappears between observations."""
    first = normalize_activity(activity_row, 'orders')
    later = {**activity_row, 'observed_timestamp': activity_row['observed_timestamp'] + timedelta(seconds=2)}
    for key in ('session_auth_id', 'client_hostname', 'connection_start_time'):
        later.pop(key)
    second = normalize_activity(later, 'orders')
    assert second['elapsed_ns'] == first['elapsed_ns'] + 2_000_000_000
    assert not {'session_auth_id', 'client_hostname', 'connection_start_time'} & second.keys()


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
    assert normalize_activity({**activity_row, **patch}, 'orders') is None


def test_obfuscation_failure(activity_row: dict, monkeypatch: pytest.MonkeyPatch):
    """An obfuscator failure must omit the sample instead of sending the original statement."""

    def fail(*_args: object) -> None:
        raise ValueError('Could not obfuscate')

    monkeypatch.setattr('datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata', fail)
    assert normalize_activity(activity_row, 'orders') is None
