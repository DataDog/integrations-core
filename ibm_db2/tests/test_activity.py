# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.ibm_db2 import activity
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


@pytest.mark.parametrize('count, expected_limit', [(1, 0), (3, 1)])
def test_activity_reader_limits(monkeypatch: pytest.MonkeyPatch, count: int, expected_limit: int):
    """Return an oldest-first prefix and report whether the extra fetched row exceeded the cap."""
    monkeypatch.setattr(activity, 'ACTIVITY_MAX_ROWS', 2)
    rows = [{'stmt_text': str(index)} for index in range(count)]
    cursor = object()
    prepare, release = Mock(return_value=cursor), Mock()
    monkeypatch.setattr(activity.ibm_db, 'prepare', prepare)
    monkeypatch.setattr(activity.ibm_db, 'execute', Mock())
    monkeypatch.setattr(activity.ibm_db, 'fetch_assoc', Mock(side_effect=[*rows, False]))
    monkeypatch.setattr(activity.ibm_db, 'free_stmt', release)
    result, stats = activity.read_activity('connection')
    assert result == rows[:2]
    assert stats == {'row_limit': expected_limit}
    prepare.assert_called_once_with(
        'connection', activity.ACTIVITY_QUERY, {activity.ibm_db.SQL_ATTR_QUERY_TIMEOUT: activity.ACTIVITY_QUERY_TIMEOUT}
    )
    release.assert_called_once_with(cursor)


@pytest.mark.parametrize(
    'text, database_bytes, expected_text, truncated',
    [
        ('SELECT 1', 8, 'SELECT 1', 'not_truncated'),
        ('é' * 8192, 8192, 'é' * 8192, 'not_truncated'),
        ('é' * 10000, 10000, 'é' * 8192, 'truncated'),
        ('中' * 6000, 12000, '中' * 5461, 'truncated'),
        ('é' * 10000, 50000, 'é' * 8192, 'truncated'),
        ('A' * 16384, 50000, 'A' * 16384, 'truncated'),
        (None, None, None, None),
    ],
)
def test_activity_reader_utf8_limit(
    monkeypatch: pytest.MonkeyPatch,
    activity_row: dict,
    text: str | None,
    database_bytes: int | None,
    expected_text: str | None,
    truncated: str | None,
):
    """Code-page expansion must not exceed the UTF-8 cap or hide either source of truncation."""
    row = {**activity_row, 'stmt_text': text, 'stmt_text_bytes': database_bytes}
    monkeypatch.setattr(activity.ibm_db, 'prepare', Mock())
    monkeypatch.setattr(activity.ibm_db, 'execute', Mock())
    monkeypatch.setattr(activity.ibm_db, 'fetch_assoc', Mock(side_effect=[row, False]))
    monkeypatch.setattr(activity.ibm_db, 'free_stmt', Mock())
    rows, _ = activity.read_activity('connection')
    assert len(rows) == 1
    assert rows[0]['stmt_text'] == expected_text
    result = normalize_activity(rows[0], 'orders')
    if truncated is None:
        assert result is None
    else:
        assert result['query_truncated'] == truncated


@pytest.mark.parametrize('stage', ['execute', 'fetch_assoc'])
def test_activity_reader_failure_releases_statement(monkeypatch: pytest.MonkeyPatch, stage: str):
    """A failed monitoring read must propagate its error and release the native statement, never return idle data."""
    cursor = object()
    monkeypatch.setattr(activity.ibm_db, 'prepare', Mock(return_value=cursor))
    monkeypatch.setattr(activity.ibm_db, 'execute', Mock())
    monkeypatch.setattr(activity.ibm_db, 'fetch_assoc', Mock())
    monkeypatch.setattr(activity.ibm_db, stage, Mock(side_effect=RuntimeError('SQLSTATE=HYT00')))
    release = Mock()
    monkeypatch.setattr(activity.ibm_db, 'free_stmt', release)
    with pytest.raises(RuntimeError, match='SQLSTATE=HYT00'):
        activity.read_activity('connection')
    release.assert_called_once_with(cursor)


@pytest.mark.parametrize('dbm, enabled', [(False, False), (False, True), (True, False), (True, True)])
def test_query_activity_registration(
    instance: dict,
    aggregator: AggregatorStub,
    monkeypatch: pytest.MonkeyPatch,
    activity_row: dict,
    dbm: bool,
    enabled: bool,
):
    """Only explicit DBM sampling submits activity with configured tags in the common envelope."""
    from datadog_checks.ibm_db2 import IbmDb2Check, query_samples

    monkeypatch.setenv('DBM_THREADED_JOB_RUN_SYNC', 'true')
    instance.update(dbm=dbm, query_metrics={'enabled': False}, query_activity={'enabled': enabled}, service='orders')
    instance['tags'] = ['custom_tag:query-activity']
    check = IbmDb2Check('ibm_db2', {}, [instance])
    source = Mock(return_value=([activity_row], {'row_limit': 0}))
    monkeypatch.setattr(query_samples, 'read_activity', source)
    if dbm:
        monkeypatch.setattr(check._query_samples._connection, 'ensure_connected', Mock())
    check.run_async_jobs(check.tags)
    events = aggregator.get_event_platform_events('dbm-activity')
    assert len(events) == source.call_count == int(dbm and enabled)
    if events:
        event = events[0]
        assert event['ddsource'] == 'ibm_db2'
        assert event['dbm_type'] == 'activity'
        assert event['service'] == 'orders'
        assert 'custom_tag:query-activity' in event['ddtags']
        assert event['host'] == check.reported_hostname
        assert event['database_instance'] == check.database_identifier
        assert event['collection_interval'] == 10
        assert event['ibm_db2_activity'][0]['database_name'] == instance['db']
        assert 'LITERAL_SECRET' not in json.dumps(event)
        assert 'RAW_SECRET' not in json.dumps(event)
        assert event['ibm_db2_activity'][0]['dd_comments'] == ['COMMENT_SECRET']
        owned_handle = object()
        check._query_samples._connection.conn = owned_handle
        with pytest.MonkeyPatch.context() as patch:
            close = Mock()
            patch.setattr(activity.ibm_db, 'close', close)
            check.cancel()
            close.assert_called_once_with(owned_handle)


@pytest.mark.parametrize('serializer_name', ['stdlib', 'orjson'])
@pytest.mark.parametrize('multibyte', [False, True])
def test_query_activity_payload_cap(
    instance: dict,
    aggregator: AggregatorStub,
    monkeypatch: pytest.MonkeyPatch,
    activity_row: dict,
    serializer_name: str,
    multibyte: bool,
):
    """Cap serialized bytes, including multibyte context, while retaining the oldest-first prefix."""
    from datadog_checks.ibm_db2 import IbmDb2Check, query_samples

    serializer = json if serializer_name == 'stdlib' else pytest.importorskip('orjson')
    monkeypatch.setattr(query_samples, 'json', serializer)
    if multibyte:
        activity_row.update(client_applname='表' * 512, client_wrkstnname='表' * 512)
    instance.update(dbm=True, query_activity={'enabled': True})
    check = IbmDb2Check('ibm_db2', {}, [instance])
    collector = check._query_samples
    monkeypatch.setattr(collector._connection, 'ensure_connected', Mock())
    rows = [activity_row, {**activity_row, 'application_handle': 42}]
    monkeypatch.setattr(query_samples, 'read_activity', lambda _connection: (rows, {'row_limit': 0}))
    collector.run_job()
    event = aggregator.get_event_platform_events('dbm-activity')[0]
    assert len(event['ibm_db2_activity']) == 2
    one_row = {**event, 'ibm_db2_activity': event['ibm_db2_activity'][:1]}
    encoded = serializer.dumps(one_row)
    limit = len(encoded.encode('utf-8') if isinstance(encoded, str) else encoded) + 16
    if multibyte:
        assert len(str(event)) < limit
    monkeypatch.setattr(query_samples, 'ACTIVITY_PAYLOAD_MAX_BYTES', limit)
    aggregator.reset()
    collector.run_job()
    capped = aggregator.get_event_platform_events('dbm-activity')[0]
    encoded = aggregator.get_event_platform_events('dbm-activity', parse_json=False)[0]
    assert len(encoded.encode('utf-8') if isinstance(encoded, str) else encoded) <= limit
    assert [row['application_handle'] for row in capped['ibm_db2_activity']] == [activity_row['application_handle']]
    aggregator.assert_metric('dd.ibm_db2.query_activity.payload_limit', value=1)


def test_query_activity_failed_read_is_not_idle(
    instance: dict, aggregator: AggregatorStub, monkeypatch: pytest.MonkeyPatch
):
    """A failed read produces no snapshot, while a subsequent successful idle read emits an empty observation."""
    from datadog_checks.ibm_db2 import IbmDb2Check, query_samples

    instance.update(dbm=True, query_activity={'enabled': True})
    check = IbmDb2Check('ibm_db2', {}, [instance])
    collector = check._query_samples
    monkeypatch.setattr(collector._connection, 'ensure_connected', Mock())
    source = Mock(side_effect=[RuntimeError('SQLSTATE=HYT00'), ([], {'row_limit': 0})])
    monkeypatch.setattr(query_samples, 'read_activity', source)
    with pytest.raises(RuntimeError, match='SQLSTATE=HYT00'):
        collector.run_job()
    assert not aggregator.get_event_platform_events('dbm-activity')
    collector.run_job()
    assert aggregator.get_event_platform_events('dbm-activity')[0]['ibm_db2_activity'] == []


@pytest.mark.parametrize('connection_error', [False, True])
def test_query_activity_error_health(
    instance: dict, aggregator: AggregatorStub, monkeypatch: pytest.MonkeyPatch, connection_error: bool
):
    """Connection and read failures report sanitized feature health without fabricating an idle snapshot."""
    from datadog_checks.ibm_db2 import IbmDb2Check, query_samples
    from datadog_checks.ibm_db2.connection import Db2ConnectionError

    monkeypatch.delenv('DBM_THREADED_JOB_RUN_SYNC', raising=False)
    instance.update(dbm=True, query_activity={'enabled': True})
    check = IbmDb2Check('ibm_db2', {}, [instance])
    collector = check._query_samples
    error = (Db2ConnectionError if connection_error else RuntimeError)('SECRET SQLSTATE=42501')
    connect = Mock(side_effect=error) if connection_error else Mock()
    monkeypatch.setattr(collector._connection, 'ensure_connected', connect)
    monkeypatch.setattr(query_samples, 'read_activity', Mock(side_effect=error))
    collector.run_job_loop(check.tags)
    collector.wait_for_completion()
    health = [event for event in aggregator.get_event_platform_events('dbm-health') if event['name'] == 'unknown_error']
    assert len(health) == 1
    assert health[0]['data']['job_name'] == 'query-activity'
    assert health[0]['data']['sqlstate'] == '42501'
    assert 'SECRET' not in json.dumps(health)
    assert not aggregator.get_event_platform_events('dbm-activity')
    check.cancel()
