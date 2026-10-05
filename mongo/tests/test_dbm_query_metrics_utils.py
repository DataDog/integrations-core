# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import json

import mock
import pytest

from datadog_checks.mongo import MongoDb
from datadog_checks.mongo.common import HostingType, StandaloneDeployment
from datadog_checks.mongo.dbm.utils import (
    get_query_stats_row_key,
    normalize_query_stats_value,
    reconstruct_command_from_query_shape,
)


class TestNormalizeQueryStatsValue:
    """Tests for normalizing $queryStats type annotations to simple '?' placeholders."""

    def test_simple_type_annotations(self):
        """Test that basic type annotations are converted to '?'."""
        assert normalize_query_stats_value("?string") == "?"
        assert normalize_query_stats_value("?number") == "?"
        assert normalize_query_stats_value("?date") == "?"
        assert normalize_query_stats_value("?bool") == "?"
        assert normalize_query_stats_value("?objectId") == "?"
        assert normalize_query_stats_value("?array") == "?"
        assert normalize_query_stats_value("?object") == "?"
        assert normalize_query_stats_value("?binData") == "?"
        assert normalize_query_stats_value("?null") == "?"
        assert normalize_query_stats_value("?regex") == "?"
        assert normalize_query_stats_value("?timestamp") == "?"

    def test_regular_string_unchanged(self):
        """Test that regular strings are not modified."""
        assert normalize_query_stats_value("hello") == "hello"
        assert normalize_query_stats_value("") == ""
        assert normalize_query_stats_value("$eq") == "$eq"
        assert normalize_query_stats_value("?unknown") == "?unknown"  # Unknown types stay unchanged

    def test_nested_dict(self):
        """Test normalization in nested dictionaries."""
        value = {"$eq": "?string", "$gt": "?number"}
        expected = {"$eq": "?", "$gt": "?"}
        assert normalize_query_stats_value(value) == expected

    def test_nested_list(self):
        """Test normalization in lists."""
        value = ["?string", "?number", "regular"]
        expected = ["?", "?", "regular"]
        assert normalize_query_stats_value(value) == expected

    def test_deeply_nested_structure(self):
        """Test normalization in deeply nested structures."""
        value = {
            "filter": {
                "$and": [{"status": {"$eq": "?string"}}, {"amount": {"$gt": "?number"}}, {"created": {"$gte": "?date"}}]
            }
        }
        expected = {
            "filter": {"$and": [{"status": {"$eq": "?"}}, {"amount": {"$gt": "?"}}, {"created": {"$gte": "?"}}]}
        }
        assert normalize_query_stats_value(value) == expected

    def test_preserves_non_string_values(self):
        """Test that non-string values are preserved."""
        assert normalize_query_stats_value(123) == 123
        assert normalize_query_stats_value(12.5) == 12.5
        assert normalize_query_stats_value(True) is True
        assert normalize_query_stats_value(None) is None


class TestReconstructCommandFromQueryShape:
    """Tests for reconstructing $currentOp-style commands from $queryStats shapes."""

    def test_find_command(self):
        """Test reconstruction of a find command."""
        query_shape = {
            "cmdNs": {"db": "test", "coll": "orders"},
            "command": "find",
            "filter": {"status": {"$eq": "?string"}},
        }
        result = reconstruct_command_from_query_shape(query_shape)

        assert result["find"] == "orders"
        assert result["$db"] == "test"
        assert result["filter"] == {"status": {"$eq": "?"}}

    def test_find_with_projection_and_sort(self):
        """Test reconstruction of find with projection and sort."""
        query_shape = {
            "cmdNs": {"db": "mydb", "coll": "users"},
            "command": "find",
            "filter": {"active": {"$eq": "?bool"}},
            "projection": {"name": "?number", "email": "?number"},
            "sort": {"created": "?number"},
        }
        result = reconstruct_command_from_query_shape(query_shape)

        assert result["find"] == "users"
        assert result["$db"] == "mydb"
        assert result["filter"] == {"active": {"$eq": "?"}}
        assert result["projection"] == {"name": "?", "email": "?"}
        assert result["sort"] == {"created": "?"}

    def test_aggregate_command(self):
        """Test reconstruction of an aggregate command."""
        query_shape = {
            "cmdNs": {"db": "analytics", "coll": "events"},
            "command": "aggregate",
            "pipeline": [
                {"$match": {"type": {"$eq": "?string"}}},
                {"$group": {"_id": "?string", "count": {"$sum": "?number"}}},
            ],
        }
        result = reconstruct_command_from_query_shape(query_shape)

        assert result["aggregate"] == "events"
        assert result["$db"] == "analytics"
        assert len(result["pipeline"]) == 2
        assert result["pipeline"][0]["$match"]["type"]["$eq"] == "?"
        assert result["pipeline"][1]["$group"]["_id"] == "?"

    def test_distinct_command(self):
        """Test reconstruction of a distinct command."""
        query_shape = {
            "cmdNs": {"db": "inventory", "coll": "products"},
            "command": "distinct",
            "key": "category",
            "filter": {"active": {"$eq": "?bool"}},
        }
        result = reconstruct_command_from_query_shape(query_shape)

        assert result["distinct"] == "products"
        assert result["$db"] == "inventory"
        assert result["key"] == "category"
        assert result["filter"]["active"]["$eq"] == "?"

    def test_count_command(self):
        """Test reconstruction of a count command."""
        query_shape = {
            "cmdNs": {"db": "logs", "coll": "access"},
            "command": "count",
            "filter": {"level": {"$eq": "?string"}},
        }
        result = reconstruct_command_from_query_shape(query_shape)

        assert result["count"] == "access"
        assert result["$db"] == "logs"
        assert result["filter"]["level"]["$eq"] == "?"

    def test_empty_query_shape(self):
        """Test handling of empty query shape."""
        assert reconstruct_command_from_query_shape({}) == {}
        assert reconstruct_command_from_query_shape(None) == {}

    def test_missing_optional_fields(self):
        """Test handling of query shape with missing optional fields."""
        query_shape = {
            "cmdNs": {"db": "test", "coll": "items"},
            "command": "find",
            # No filter, projection, sort, etc.
        }
        result = reconstruct_command_from_query_shape(query_shape)

        assert result["find"] == "items"
        assert result["$db"] == "test"
        assert "filter" not in result
        assert "projection" not in result

    def test_with_limit_and_skip(self):
        """Test reconstruction with limit and skip."""
        query_shape = {
            "cmdNs": {"db": "test", "coll": "items"},
            "command": "find",
            "filter": {},
            "limit": "?number",
            "skip": "?number",
        }
        result = reconstruct_command_from_query_shape(query_shape)

        assert result["find"] == "items"
        assert result["limit"] == "?"
        assert result["skip"] == "?"


class TestGetQueryStatsRowKey:
    """Tests for generating unique keys for query metrics rows."""

    def test_basic_key_generation(self):
        """Test basic key generation."""
        row = {"query_signature": "abc123", "db_name": "testdb", "collection": "users"}
        key = get_query_stats_row_key(row)
        assert key == ("abc123", "testdb", "users")

    def test_missing_fields(self):
        """Test key generation with missing fields."""
        row = {"query_signature": "xyz"}
        key = get_query_stats_row_key(row)
        assert key == ("xyz", "", "")

    def test_empty_row(self):
        """Test key generation with empty row."""
        row = {}
        key = get_query_stats_row_key(row)
        assert key == ("", "", "")

    def test_key_uniqueness(self):
        """Test that different combinations produce different keys."""
        row1 = {"query_signature": "sig1", "db_name": "db1", "collection": "coll1"}
        row2 = {"query_signature": "sig1", "db_name": "db1", "collection": "coll2"}
        row3 = {"query_signature": "sig1", "db_name": "db2", "collection": "coll1"}

        assert get_query_stats_row_key(row1) != get_query_stats_row_key(row2)
        assert get_query_stats_row_key(row1) != get_query_stats_row_key(row3)
        assert get_query_stats_row_key(row2) != get_query_stats_row_key(row3)


@pytest.mark.parametrize(
    'command,shape,expected',
    [
        ('insert', {'documents': ['?object']}, {'documents': ['?']}),
        (
            'update',
            {'q': {'x': '?number'}, 'u': {'$set': {'y': '?string'}}, 'multi': False, 'upsert': True},
            {'updates': [{'q': {'x': '?'}, 'u': {'$set': {'y': '?'}}, 'multi': False, 'upsert': True}]},
        ),
        (
            'update',
            {'q': {}, 'u': [{'$set': {'x': '?number'}}], 'arrayFilters': [{'i': '?number'}], 'let': {'v': '?number'}},
            {'updates': [{'q': {}, 'u': [{'$set': {'x': '?'}}], 'arrayFilters': [{'i': '?'}]}], 'let': {'v': '?'}},
        ),
        ('delete', {'q': {'x': '?number'}, 'limit': 1}, {'deletes': [{'q': {'x': '?'}, 'limit': 1}]}),
        ('count', {'query': {'x': '?number'}}, {'query': {'x': '?'}}),
        ('distinct', {'query': {'x': '?number'}, 'key': 'x'}, {'query': {'x': '?'}, 'key': 'x'}),
        ('aggregate', {'pipeline': [], 'allowPartialResults': False}, {'pipeline': [], 'allowPartialResults': False}),
    ],
)
def test_reconstruct_query_stats_commands(command: str, shape: dict, expected: dict):
    # Losing predicates or update expressions merges unrelated queries into one signature.
    shape = {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': command, **shape}
    assert reconstruct_command_from_query_shape(shape) == {command: 'orders', '$db': 'test', **expected}


@pytest.mark.parametrize('nested', [False, True], ids=['mongodb8', 'mongodb9'])
def test_query_stats_metric_deltas(nested: bool):
    # Both response layouts must produce numeric interval metrics, including zero-valued counters.
    check = MongoDb(
        'mongo', {}, [{'hosts': ['localhost'], 'database': 'test', 'dbm': True, 'cluster_name': 'test-cluster'}]
    )
    check.deployment_type = StandaloneDeployment(HostingType.SELF_HOSTED)
    collector = check._query_metrics
    groups = {
        'cursor': {'firstResponseExecMicros': {'sum': 12}},
        'queryExec': {'docsExamined': {'sum': 8}, 'docsReturned': {'sum': 2}, 'keysExamined': {'sum': 0}},
        'queryPlanner': {'usedDisk': {'true': 0, 'false': 2}, 'planningTimeMicros': {'sum': 6}},
    }
    metrics = {'execCount': 2, 'totalExecMicros': {'sum': 20}, 'workingTimeMillis': {'sum': 10}}
    if nested:
        metrics.update(groups)
        metrics['writes'] = {'nModified': {'sum': 4}, 'nInserted': {'sum': 0}}
    else:
        for group in groups.values():
            metrics.update(group)
    row = {
        'key': {'queryShape': {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': 'find', 'filter': {}}},
        'keyHash': 'key-a',
        'metrics': metrics,
    }
    second = copy.deepcopy(row)
    second['metrics']['execCount'] = 3
    second['metrics']['totalExecMicros']['sum'] = 35
    second['metrics']['workingTimeMillis']['sum'] = 14
    (second['metrics']['queryExec'] if nested else second['metrics'])['docsExamined']['sum'] = 11
    if nested:
        second['metrics']['writes']['nModified']['sum'] = 7
    with mock.patch.object(collector, '_load_query_stats', side_effect=[[row], [second]]):
        assert collector._collect_metrics_rows() == []
        (result,) = collector._collect_metrics_rows()
    assert result['exec_count'] == 1
    assert result['total_exec_micros_sum'] == 15
    assert result['working_time_millis_sum'] == 4
    assert result['docs_examined_sum'] == 3
    assert result['keys_examined_sum'] == 0
    assert result['used_disk_count'] == 0
    if nested:
        assert result['docs_modified_sum'] == 3
        assert result['docs_inserted_sum'] == 0
    json.dumps(result)


def test_query_stats_independent_entries_and_sparse_metrics():
    # Evicting one client's entry must not discard another client's deltas or duplicate full query text.
    check = MongoDb(
        'mongo', {}, [{'hosts': ['localhost'], 'database': 'test', 'dbm': True, 'cluster_name': 'test-cluster'}]
    )
    check.deployment_type = StandaloneDeployment(HostingType.SELF_HOSTED)
    collector = check._query_metrics
    shape = {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': 'find', 'filter': {}}
    first = [
        {'key': {'queryShape': shape}, 'keyHash': 'a', 'metrics': {'execCount': 10}},
        {'key': {'queryShape': shape}, 'keyHash': 'b', 'metrics': {'execCount': 2, 'docsExamined': {'sum': 5}}},
    ]
    normalized = collector._normalize_rows(first)
    assert len(list(collector._rows_to_fqt_events(normalized))) == 1
    second = copy.deepcopy(first[1])
    second['metrics']['execCount'] = 3
    second['metrics']['docsExamined']['sum'] = 9
    with mock.patch.object(collector, '_load_query_stats', side_effect=[first, [second]]):
        assert collector._collect_metrics_rows() == []
        (result,) = collector._collect_metrics_rows()
    assert result['exec_count'] == 1
    assert result['docs_examined_sum'] == 4


@pytest.mark.parametrize('change', ['metric_added', 'metric_removed', 'entry_recreated'])
def test_query_stats_reestablishes_baseline(change: str):
    # New counters or recreated entries must not emit their lifetime totals as interval deltas.
    check = MongoDb('mongo', {}, [{'hosts': ['localhost'], 'database': 'test'}])
    check.deployment_type = StandaloneDeployment(HostingType.SELF_HOSTED)
    collector = check._query_metrics
    first = {
        'key': {'queryShape': {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': 'find'}},
        'keyHash': 'a',
        'metrics': {'execCount': 10, 'firstSeenTimestamp': '2026-10-01T00:00:00'},
    }
    if change == 'metric_removed':
        first['metrics']['planningTimeMicros'] = {'sum': 500}
    second = copy.deepcopy(first)
    second['metrics']['execCount'] = 11
    if change == 'metric_added':
        second['metrics']['planningTimeMicros'] = {'sum': 1000}
    elif change == 'metric_removed':
        del second['metrics']['planningTimeMicros']
    else:
        second['metrics']['firstSeenTimestamp'] = '2026-10-02T00:00:00'
    third = copy.deepcopy(second)
    third['metrics']['execCount'] = 12
    if change == 'metric_added':
        third['metrics']['planningTimeMicros']['sum'] = 1020
    unchanged = copy.deepcopy(first)
    unchanged['keyHash'] = 'b'
    unchanged['metrics']['planningTimeMicros'] = {'sum': 100}
    polls = []
    for i, row in enumerate((first, second, third)):
        other = copy.deepcopy(unchanged)
        other['metrics']['execCount'] += i
        other['metrics']['planningTimeMicros']['sum'] += i * 5
        polls.append([row, other])
    with mock.patch.object(collector, '_load_query_stats', side_effect=polls):
        assert collector._collect_metrics_rows() == []
        (unaffected,) = collector._collect_metrics_rows()
        assert unaffected['key_hash'] == 'b'
        assert unaffected['exec_count'] == 1
        assert unaffected['planning_time_micros_sum'] == 5
        result = next(row for row in collector._collect_metrics_rows() if row['key_hash'] == 'a')
    assert result['exec_count'] == 1
    if change == 'metric_added':
        assert result['planning_time_micros_sum'] == 20
