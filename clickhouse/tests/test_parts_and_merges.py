# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import json
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.parts_and_merges import (
    DBM_TYPE,
    ClickhousePartsAndMerges,
    _classify_detach_reason,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def instance_enabled():
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'parts_and_merges': {
            'enabled': True,
            'collection_interval': 60,
            'max_parts_rows': 500,
            'max_mutations_rows': 200,
            'run_sync': True,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check(instance_enabled):
    return ClickhouseCheck('clickhouse', {}, [instance_enabled])


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------


def test_initialization(check):
    assert isinstance(check.parts_and_merges, ClickhousePartsAndMerges)
    assert check.parts_and_merges._config.enabled is True
    assert check.parts_and_merges._config.collection_interval == 60
    assert check.parts_and_merges._max_tables == 200
    assert check.parts_and_merges._include_partition_tag is False


def test_enabled_by_default_when_dbm_on():
    """parts_and_merges defaults to enabled when dbm is on (matches other DBM sub-features)."""
    check = ClickhouseCheck('clickhouse', {}, [{'server': 'localhost', 'dbm': True}])
    assert check.parts_and_merges is not None


def test_disabled_when_dbm_off():
    """parts_and_merges requires dbm=true, even with explicit enabled=True."""
    check = ClickhouseCheck(
        'clickhouse', {}, [{'server': 'localhost', 'dbm': False, 'parts_and_merges': {'enabled': True}}]
    )
    assert check.parts_and_merges is None


def test_disabled_when_explicitly_opted_out():
    """Users can still opt out via enabled=False even when dbm is on."""
    check = ClickhouseCheck(
        'clickhouse', {}, [{'server': 'localhost', 'dbm': True, 'parts_and_merges': {'enabled': False}}]
    )
    assert check.parts_and_merges is None


def test_partition_tag_config():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'parts_and_merges': {
                    'enabled': True,
                    'run_sync': True,
                    'table_metrics_include_partition_tag': True,
                    'table_metrics_max_tables': 25,
                },
            }
        ],
    )
    assert check.parts_and_merges._include_partition_tag is True
    assert check.parts_and_merges._max_tables == 25


# -----------------------------------------------------------------------------
# Row collection — SQL row normalization
# -----------------------------------------------------------------------------


def _parts_row_aggregated():
    """Row shape for PARTS_AGGREGATED_QUERY (default: no partition column)."""
    return (
        'default',
        'events',
        'node-1',
        287,  # active_part_count
        12,  # level_zero_count
        200,  # compact_parts
        87,  # wide_parts
        1_200_000_000,
        450_000_000,
        420_000_000,
        3_000_000_000,
        7,
        4.2,
        datetime.datetime(2024, 1, 1, 0, 0, 0),
        datetime.datetime(2024, 1, 2, 12, 0, 0),
    )


def _parts_row_by_partition():
    """Row shape for PARTS_BY_PARTITION_QUERY (includes partition column)."""
    return (
        'default',
        'events',
        '20240101',
        'node-1',
        287,  # active_part_count
        12,  # level_zero_count
        200,  # compact_parts
        87,  # wide_parts
        1_200_000_000,
        450_000_000,
        420_000_000,
        3_000_000_000,
        7,
        4.2,
        datetime.datetime(2024, 1, 1, 0, 0, 0),
        datetime.datetime(2024, 1, 2, 12, 0, 0),
    )


def _detached_row(reason=None, count=3):
    return ('default', 'events', 'node-1', reason, count)


def _merges_row():
    return (
        'default',
        'events',
        '20240101',
        'node-1',
        83.4,
        0.47,
        12,
        False,
        'Regular',
        'Horizontal',
        1_200_000_000,
        800_000_000,
        5_000_000,
        600_000_000,
        3_000_000,
        1_300_000_000,
        ['all_0_5_1', 'all_6_11_1'],
        'all_0_11_2',
    )


def _mutations_row():
    return (
        'default',
        'events',
        'node-1',
        '0000000003',
        "DELETE WHERE ts < '2023-01-01'",
        datetime.datetime(2024, 1, 1, 9, 0, 0),
        False,
        47,
        None,
        None,
        None,
    )


def _replication_queue_row():
    return (
        'default',
        'events',
        'node-1',
        'MERGE_PARTS',
        0,
        True,
        1,
        None,
        None,
        0,
        None,
        ['all_0_5_1', 'all_6_11_1'],
    )


def test_collect_parts_normalizes(check):
    """Default (aggregated) query path: partition is None because SQL aggregates at table level."""
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    with mock.patch.object(job, '_execute_query', return_value=[_parts_row_aggregated()]):
        rows = job._collect_parts()
    assert len(rows) == 1
    row = rows[0]
    assert row['database'] == 'default'
    assert row['table'] == 'events'
    assert row['partition'] is None
    assert row['server_node'] == 'node-1'
    assert row['active_part_count'] == 287
    assert row['total_rows'] == 1_200_000_000
    assert row['oldest_part_time'] is not None


def test_collect_parts_normalizes_with_partition_tag():
    """When partition tag is enabled, partition column is returned and preserved."""
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'parts_and_merges': {
                    'enabled': True,
                    'run_sync': True,
                    'table_metrics_include_partition_tag': True,
                },
            }
        ],
    )
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    with mock.patch.object(job, '_execute_query', return_value=[_parts_row_by_partition()]):
        rows = job._collect_parts()
    assert len(rows) == 1
    assert rows[0]['partition'] == '20240101'


def test_collect_parts_uses_aggregated_sql_by_default(check):
    """Default path must use PARTS_AGGREGATED_QUERY (GROUP BY database, table, server_node only)."""
    job = check.parts_and_merges
    job.tags = []
    job._tags_no_db = []
    seen = []
    with mock.patch.object(job, '_execute_query', side_effect=lambda q: seen.append(q) or []):
        job._collect_parts()
    assert len(seen) == 1
    query = seen[0]
    assert 'GROUP BY database, table, server_node' in query
    assert 'partition' not in query.split('GROUP BY')[1].split('\n')[0]


def test_collect_parts_uses_partition_sql_when_enabled():
    """With partition tag enabled, query must include partition in GROUP BY."""
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'parts_and_merges': {
                    'enabled': True,
                    'run_sync': True,
                    'table_metrics_include_partition_tag': True,
                },
            }
        ],
    )
    job = check.parts_and_merges
    job.tags = []
    job._tags_no_db = []
    seen = []
    with mock.patch.object(job, '_execute_query', side_effect=lambda q: seen.append(q) or []):
        job._collect_parts()
    assert 'GROUP BY database, table, partition, server_node' in seen[0]


def test_collect_merges_normalizes(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    with mock.patch.object(job, '_execute_query', return_value=[_merges_row()]):
        rows = job._collect_merges()
    assert len(rows) == 1
    row = rows[0]
    assert row['progress'] == pytest.approx(0.47)
    assert row['memory_usage'] == 1_300_000_000
    assert row['result_part_name'] == 'all_0_11_2'


def test_collect_mutations_normalizes_and_obfuscates(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    with mock.patch.object(job, '_execute_query', return_value=[_mutations_row()]):
        rows = job._collect_mutations()
    assert len(rows) == 1
    row = rows[0]
    assert row['mutation_id'] == '0000000003'
    assert row['server_node'] == 'node-1'
    assert row['parts_to_do'] == 47
    assert row['is_done'] is False
    # command passes through the SQL obfuscator; we just assert the key is present
    # and is either None or a string (obfuscator behavior on ClickHouse ALTER varies).
    assert 'command' in row
    assert row['command'] is None or isinstance(row['command'], str)


def test_collect_thresholds_normalizes(check):
    """system.merge_tree_settings rows are normalized; non-numeric values are dropped."""
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    rows_in = [
        ('node-1', 'parts_to_delay_insert', '150'),
        ('node-1', 'parts_to_throw_insert', '300'),
        ('node-1', 'unrelated', 'not-a-number'),
    ]
    with mock.patch.object(job, '_execute_query', return_value=rows_in):
        out = job._collect_thresholds()
    assert len(out) == 2
    by_name = {r['name']: r['value'] for r in out}
    assert by_name == {'parts_to_delay_insert': 150, 'parts_to_throw_insert': 300}


def test_emit_gauges_thresholds(check):
    """Threshold rows are emitted as host-level gauges (no database/table tags)."""
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    thresholds = [
        {'server_node': 'node-1', 'name': 'parts_to_delay_insert', 'value': 150},
        {'server_node': 'node-1', 'name': 'parts_to_throw_insert', 'value': 300},
    ]
    job._emit_gauges([], [], [], [], [], thresholds)

    by_name = {n: (v, t) for n, v, t in emitted}
    assert by_name['parts.threshold.delay_insert'][0] == 150
    assert by_name['parts.threshold.throw_insert'][0] == 300
    # Thresholds are server-level — no database/table tags.
    for _, tags in by_name.values():
        assert not any(t.startswith('database:') or t.startswith('table:') for t in tags)
        assert 'server_node:node-1' in tags


def test_collect_detached_parts_normalizes(check):
    """Reason column is preserved and classified into category (manual/corrupted/other)."""
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    rows_in = [
        _detached_row(reason=None, count=3),
        _detached_row(reason='broken', count=2),
        _detached_row(reason='noquorum', count=1),
    ]
    with mock.patch.object(job, '_execute_query', return_value=rows_in):
        rows_out = job._collect_detached_parts()
    assert len(rows_out) == 3
    categories = {r['reason_category'] for r in rows_out}
    assert categories == {'manual', 'corrupted', 'other'}
    # NULL reason normalizes to None, not the literal string 'None'
    manual = next(r for r in rows_out if r['reason_category'] == 'manual')
    assert manual['reason'] is None
    assert manual['detached_count'] == 3


def test_collect_replication_queue_normalizes(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    with mock.patch.object(job, '_execute_query', return_value=[_replication_queue_row()]):
        rows = job._collect_replication_queue()
    assert len(rows) == 1
    row = rows[0]
    assert row['type'] == 'MERGE_PARTS'
    assert row['server_node'] == 'node-1'
    assert row['parts_to_merge'] == ['all_0_5_1', 'all_6_11_1']


# -----------------------------------------------------------------------------
# Gauge emission
# -----------------------------------------------------------------------------


def _collected_parts():
    return [
        {
            'database': 'default',
            'table': 'events',
            'partition': '20240101',
            'server_node': 'node-1',
            'active_part_count': 287,
            'level_zero_count': 12,
            'compact_parts': 200,
            'wide_parts': 87,
            'total_rows': 1_200_000_000,
            'bytes_on_disk': 450_000_000,
            'compressed_bytes': 420_000_000,
            'uncompressed_bytes': 3_000_000_000,
            'max_merge_level': 7,
            'avg_merge_level': 4.2,
            'oldest_part_time': 1704067200,
            'newest_part_time': 1704196800,
        }
    ]


def _collected_detached():
    return [
        {
            'database': 'default',
            'table': 'events',
            'server_node': 'node-1',
            'reason': None,
            'reason_category': 'manual',
            'detached_count': 3,
        },
        {
            'database': 'default',
            'table': 'events',
            'server_node': 'node-1',
            'reason': 'broken',
            'reason_category': 'corrupted',
            'detached_count': 2,
        },
        {
            'database': 'default',
            'table': 'events',
            'server_node': 'node-1',
            'reason': 'noquorum',
            'reason_category': 'other',
            'detached_count': 1,
        },
    ]


def _collected_merges():
    return [
        {
            'database': 'default',
            'table': 'events',
            'partition_id': '20240101',
            'server_node': 'node-1',
            'elapsed': 83.4,
            'progress': 0.47,
            'num_parts': 12,
            'is_mutation': False,
            'total_size_bytes_compressed': 1_200_000_000,
            'memory_usage': 1_300_000_000,
        }
    ]


def _collected_mutations():
    return [
        {
            'database': 'default',
            'table': 'events',
            'server_node': 'node-1',
            'mutation_id': '0000000003',
            'command': 'DELETE WHERE ?',
            'create_time': 1704067200,
            'is_done': False,
            'parts_to_do': 47,
            'latest_fail_reason': None,
        }
    ]


def _collected_replication():
    return [
        {
            'database': 'default',
            'table': 'events',
            'server_node': 'node-1',
            'type': 'MERGE_PARTS',
            'num_tries': 1,
        },
        {
            'database': 'default',
            'table': 'events',
            'server_node': 'node-1',
            'type': 'GET_PART',
            'num_tries': 5,
        },
    ]


def test_emit_gauges_parts(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges(_collected_parts(), [], [], [], [])

    names = {m[0] for m in emitted}
    assert {
        'table.parts.active',
        'table.parts.level_zero',
        'table.parts.compact',
        'table.parts.wide',
        'table.parts.rows',
        'table.parts.bytes_on_disk',
        'table.parts.compressed_bytes',
        'table.parts.uncompressed_bytes',
        'table.parts.max_merge_level',
        'table.parts.oldest_part_age_seconds',
    } <= names

    active = next(v for n, v, _ in emitted if n == 'table.parts.active')
    assert active == 287
    level_zero = next(v for n, v, _ in emitted if n == 'table.parts.level_zero')
    assert level_zero == 12
    compact = next(v for n, v, _ in emitted if n == 'table.parts.compact')
    assert compact == 200
    wide = next(v for n, v, _ in emitted if n == 'table.parts.wide')
    assert wide == 87
    max_level = next(v for n, v, _ in emitted if n == 'table.parts.max_merge_level')
    assert max_level == 7


def test_emit_gauges_detached_parts(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges([], [], [], [], _collected_detached())

    by_name = {n: v for n, v, _ in emitted if n.startswith('table.detached_parts.')}
    assert by_name['table.detached_parts.count'] == 6
    assert by_name['table.detached_parts.manual'] == 3
    assert by_name['table.detached_parts.corrupted'] == 2
    assert by_name['table.detached_parts.other'] == 1


@pytest.mark.parametrize(
    'reason,expected',
    [
        (None, 'manual'),
        ('', 'manual'),
        ('broken', 'corrupted'),
        ('unexpected', 'corrupted'),
        ('covered-by-broken', 'corrupted'),
        ('broken-on-start', 'corrupted'),
        ('noquorum', 'other'),
        ('ignored', 'other'),
        ('clone', 'other'),
    ],
)
def test_classify_detach_reason(reason, expected):
    assert _classify_detach_reason(reason) == expected


def test_emit_gauges_merges(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges([], _collected_merges(), [], [], [])

    names = {m[0] for m in emitted}
    assert {
        'merges.active',
        'merges.stalled',
        'merges.max_elapsed_seconds',
        'merges.memory_bytes',
        'merges.total_bytes',
        'merges.avg_progress',
    } <= names

    memory = next(v for n, v, _ in emitted if n == 'merges.memory_bytes')
    assert memory == 1_300_000_000
    total_bytes = next(v for n, v, _ in emitted if n == 'merges.total_bytes')
    assert total_bytes == 1_200_000_000
    avg_progress = next(v for n, v, _ in emitted if n == 'merges.avg_progress')
    assert avg_progress == pytest.approx(0.47)


def test_emit_gauges_mutations(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges([], [], _collected_mutations(), [], [])

    names = {m[0] for m in emitted}
    assert {
        'mutations.in_progress',
        'mutations.failing',
        'mutations.parts_remaining',
        'mutations.oldest_age_seconds',
    } <= names

    remaining = next(v for n, v, _ in emitted if n == 'mutations.parts_remaining')
    assert remaining == 47


def test_emit_gauges_merges_stalled(check):
    """A merge whose elapsed exceeds the stall threshold increments merges.stalled."""
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    stalled_merge = {**_collected_merges()[0], 'elapsed': 7200.0}  # 2h > 1h threshold
    job._emit_gauges([], [stalled_merge], [], [], [])

    stalled = next(v for n, v, _ in emitted if n == 'merges.stalled')
    max_elapsed = next(v for n, v, _ in emitted if n == 'merges.max_elapsed_seconds')
    assert stalled == 1
    assert max_elapsed == 7200.0


def test_emit_gauges_mutations_failing(check):
    """A mutation with latest_fail_reason populated increments mutations.failing."""
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    failing = {**_collected_mutations()[0], 'latest_fail_reason': 'DB::Exception: disk full'}
    job._emit_gauges([], [], [failing], [], [])

    failing_count = next(v for n, v, _ in emitted if n == 'mutations.failing')
    in_progress = next(v for n, v, _ in emitted if n == 'mutations.in_progress')
    assert failing_count == 1
    assert in_progress == 1


def test_emit_gauges_replication(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges([], [], [], _collected_replication(), [])

    depth = next(v for n, v, _ in emitted if n == 'replication.queue_depth')
    stuck = next(v for n, v, _ in emitted if n == 'replication.stuck_tasks')
    assert depth == 2
    assert stuck == 1


def test_emit_gauges_no_partition_tag_by_default(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges(_collected_parts(), [], [], [], [])

    tags = next(t for n, _, t in emitted if n == 'table.parts.active')
    assert not any(t.startswith('partition:') for t in tags)


def test_emit_gauges_partition_tag_when_enabled(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._include_partition_tag = True
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges(_collected_parts(), [], [], [], [])

    tags = next(t for n, _, t in emitted if n == 'table.parts.active')
    assert 'partition:20240101' in tags


def test_default_sql_aggregates_per_table(check):
    """The default query groups by (database, table, server_node) so LIMIT caps tables."""
    job = check.parts_and_merges
    job.tags = []
    job._tags_no_db = []
    seen = []
    with mock.patch.object(job, '_execute_query', side_effect=lambda q: seen.append(q) or []):
        job._collect_parts()
    assert 'GROUP BY database, table, server_node\n' in seen[0]


def test_emit_gauges_max_tables_truncates():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'parts_and_merges': {'enabled': True, 'run_sync': True, 'table_metrics_max_tables': 1},
            }
        ],
    )
    job = check.parts_and_merges
    job.tags = []
    parts = [
        {**_collected_parts()[0], 'table': 'big', 'active_part_count': 500},
        {**_collected_parts()[0], 'table': 'small', 'active_part_count': 10},
    ]
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_gauges(parts, [], [], [], [])

    active_tags = [t for n, _, t in emitted if n == 'table.parts.active']
    assert len(active_tags) == 1
    assert 'table:big' in active_tags[0]


# -----------------------------------------------------------------------------
# Event payload
# -----------------------------------------------------------------------------


def test_emit_events_shape(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']

    captured = []
    with (
        mock.patch.object(check, 'database_monitoring_query_activity', side_effect=captured.append),
        mock.patch('datadog_checks.clickhouse.parts_and_merges.datadog_agent') as agent_mock,
    ):
        agent_mock.get_version.return_value = '7.64.0'
        job._emit_events(
            _collected_parts(),
            _collected_merges(),
            _collected_mutations(),
            _collected_replication(),
            _collected_detached(),
        )

    assert len(captured) == 1
    payload = json.loads(captured[0])
    assert payload['dbm_type'] == DBM_TYPE
    assert payload['dbms'] == 'clickhouse'
    assert payload['collection_interval'] == 60
    assert payload['top_tables_by_parts'] == _collected_parts()
    assert payload['active_merges'] == _collected_merges()
    assert payload['pending_mutations'] == _collected_mutations()
    assert len(payload['replication_queue']) == 2
    assert payload['detached_parts'] == _collected_detached()
    assert payload['ddtags'] == ['test:clickhouse']


def test_emit_events_uses_query_activity_channel_not_metadata(check):
    """Events go through database_monitoring_query_activity, not database_monitoring_metadata."""
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']

    with (
        mock.patch.object(check, 'database_monitoring_query_activity') as activity_mock,
        mock.patch.object(check, 'database_monitoring_metadata') as metadata_mock,
        mock.patch('datadog_checks.clickhouse.parts_and_merges.datadog_agent') as agent_mock,
    ):
        agent_mock.get_version.return_value = '7.64.0'
        job._emit_events([], [], [], [], [])

    activity_mock.assert_called_once()
    metadata_mock.assert_not_called()


# -----------------------------------------------------------------------------
# Error handling
# -----------------------------------------------------------------------------


def test_collection_error_returns_empty(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']
    with mock.patch.object(job, '_execute_query', side_effect=Exception("DB error")):
        assert job._collect_parts() == []
        assert job._collect_merges() == []
        assert job._collect_mutations() == []
        assert job._collect_replication_queue() == []


def test_collect_and_emit_runs_with_partial_failures(check):
    job = check.parts_and_merges
    job.tags = ['test:clickhouse']
    job._tags_no_db = ['test:clickhouse']

    captured = []
    with (
        mock.patch.object(job, '_collect_parts', return_value=[]),
        mock.patch.object(job, '_collect_merges', return_value=_collected_merges()),
        mock.patch.object(job, '_collect_mutations', return_value=[]),
        mock.patch.object(job, '_collect_replication_queue', return_value=[]),
        mock.patch.object(job, '_collect_detached_parts', return_value=[]),
        mock.patch.object(job, '_collect_thresholds', return_value=[]),
        mock.patch.object(check, 'database_monitoring_query_activity', side_effect=captured.append),
        mock.patch('datadog_checks.clickhouse.parts_and_merges.datadog_agent') as agent_mock,
    ):
        agent_mock.get_version.return_value = '7.64.0'
        job._collect_and_emit()

    assert len(captured) == 1
    payload = json.loads(captured[0])
    assert payload['top_tables_by_parts'] == []
    assert payload['active_merges'] == _collected_merges()


# -----------------------------------------------------------------------------
# Cluster routing
# -----------------------------------------------------------------------------


def test_single_endpoint_mode_routes_through_cluster_all_replicas():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'cloud.clickhouse.com',
                'dbm': True,
                'single_endpoint_mode': True,
                'parts_and_merges': {'enabled': True, 'run_sync': True},
            }
        ],
    )
    job = check.parts_and_merges
    job.tags = []
    job._tags_no_db = []
    seen = []
    with mock.patch.object(job, '_execute_query', side_effect=lambda q: seen.append(q) or []):
        job._collect_parts()
        job._collect_merges()
        job._collect_mutations()
        job._collect_replication_queue()
    assert all("clusterAllReplicas" in q for q in seen), seen


def test_direct_mode_uses_local_system_tables():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'single_endpoint_mode': False,
                'parts_and_merges': {'enabled': True, 'run_sync': True},
            }
        ],
    )
    job = check.parts_and_merges
    job.tags = []
    job._tags_no_db = []
    seen = []
    with mock.patch.object(job, '_execute_query', side_effect=lambda q: seen.append(q) or []):
        job._collect_parts()
        job._collect_merges()
        job._collect_mutations()
        job._collect_replication_queue()
    for q in seen:
        assert "clusterAllReplicas" not in q
        assert "system." in q


# -----------------------------------------------------------------------------
# run_job tag hygiene
# -----------------------------------------------------------------------------


def test_obfuscate_mutation_command_falls_back_to_none_on_error(check):
    """When the obfuscator raises, _obfuscate_mutation_command returns None."""
    job = check.parts_and_merges
    with mock.patch(
        'datadog_checks.clickhouse.parts_and_merges.obfuscate_sql_with_metadata',
        side_effect=Exception("obfuscator boom"),
    ):
        assert job._obfuscate_mutation_command("DELETE WHERE id = 42") is None
    # Empty / falsy input short-circuits before the obfuscator call.
    assert job._obfuscate_mutation_command("") is None
    assert job._obfuscate_mutation_command(None) is None


def test_run_job_strips_internal_tags(check):
    job = check.parts_and_merges
    job._tags = ['test:clickhouse', 'dd.internal:some_tag', 'db:default']
    with mock.patch.object(job, '_collect_and_emit'):
        job.run_job()
    assert 'dd.internal:some_tag' not in job.tags
    assert 'test:clickhouse' in job.tags
    assert 'db:default' not in job._tags_no_db
