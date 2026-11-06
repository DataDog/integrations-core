# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import json

import mock
import pytest
from bson import json_util, regex

from datadog_checks.mongo import MongoDb
from datadog_checks.mongo.common import HostingType, StandaloneDeployment
from datadog_checks.mongo.dbm.utils import (
    get_query_stats_row_key,
    normalize_query_stats_value,
    obfuscate_command,
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
        ('aggregate', {'pipeline': [], 'allowPartialResults': False}, {'pipeline': [], 'allowPartialResults': False}),
    ],
)
def test_reconstruct_query_stats_commands(command: str, shape: dict, expected: dict):
    shape = {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': command, **shape}
    assert reconstruct_command_from_query_shape(shape) == {command: 'orders', '$db': 'test', **expected}


@pytest.mark.parametrize(
    'command,shape,expected',
    [
        (
            'update',
            {'q': {'x': '?number'}, 'u': {'$set': {'y': '?string'}}, 'multi': False, 'upsert': True},
            {'q': {'x': '?'}, 'u': {'$set': {'y': '?'}}, 'multi': False, 'upsert': True},
        ),
        (
            'update',
            {'q': {}, 'u': [{'$set': {'x': '?number'}}], 'arrayFilters': [{'i': '?number'}], 'let': {'v': '?number'}},
            {'q': {}, 'u': [{'$set': {'x': '?'}}], 'arrayFilters': [{'i': '?'}]},
        ),
        (
            'delete',
            {'q': {'x': '?number'}, 'limit': 1, 'collation': {'locale': 'en', 'strength': 2}},
            {'q': {'x': '?'}, 'limit': 1, 'collation': {'locale': 'en', 'strength': 2}},
        ),
    ],
)
def test_reconstruct_write_query_stats_commands(command: str, shape: dict, expected: dict):
    # Match MongoDB's observed per-statement command structure so writes can share signatures across sources.
    shape = {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': command, **shape}
    assert reconstruct_command_from_query_shape(shape) == expected


@pytest.mark.parametrize('statement', [{'u': {'$set': {'value': 3}}, 'multi': False}, {'limit': 1}])
@pytest.mark.parametrize('logical_operator', [None, '$and', '$or', '$nor'])
def test_write_statement_equality_signature(statement: dict, logical_operator: str | None):
    # Equivalent write predicates and shard bookkeeping must not split query metrics from samples.
    shorthand = {'_id': 1}
    explicit = {'_id': {'$eq': 1}}
    if logical_operator:
        shorthand = {logical_operator: [shorthand]}
        explicit = {logical_operator: [explicit]}
    observed = {'q': shorthand, 'includeQueryStatsMetricsForOpIndex': 0, **statement}
    original = copy.deepcopy(observed)
    assert json.loads(obfuscate_command(observed)) == json.loads(obfuscate_command({'q': explicit, **statement}))
    assert observed == original


def test_write_statement_preserves_other_expressions():
    # Normalizing predicates must not rewrite literal objects, regexes, or update expressions.
    command = {
        'q': {
            'document': {'$eq': {'nested': 1}},
            'array': {'$eq': [1, 2]},
            'regex': {'$eq': regex.Regex('a')},
            'range': {'$gt': 1},
            '$expr': {'$eq': ['$a', '$b']},
        },
        'u': [{'$set': {'equal': {'$eq': ['$a', '$b']}}}],
    }
    assert json_util.loads(obfuscate_command(command)) == command


@pytest.mark.parametrize('command', ['find', 'distinct'])
def test_read_statement_preserves_predicates(command: str):
    # Write normalization must preserve existing read query signatures.
    statement = {command: 'orders', 'filter': {'_id': {'$eq': 1}}, 'query': {'_id': {'$eq': 1}}}
    assert json.loads(obfuscate_command(statement)) == statement


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


@pytest.mark.parametrize('write_first', [True, False], ids=['write-first', 'read-first'])
def test_query_stats_mixed_read_write_deltas(write_first: bool):
    # Different read/write columns must not crash collection or return cumulative values as interval metrics.
    check = MongoDb(
        'mongo', {}, [{'hosts': ['localhost'], 'database': 'test', 'dbm': True, 'cluster_name': 'test-cluster'}]
    )
    check.deployment_type = StandaloneDeployment(HostingType.SELF_HOSTED)
    collector = check._query_metrics
    rows = [
        {
            'key': {'queryShape': {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': 'insert'}},
            'metrics': {'execCount': 2, 'writes': {'nInserted': {'sum': 7}}},
        },
        {
            'key': {'queryShape': {'cmdNs': {'db': 'test', 'coll': 'orders'}, 'command': 'find', 'filter': {}}},
            'metrics': {'execCount': 2, 'queryExec': {'docsReturned': {'sum': 11}}},
        },
    ]
    second = copy.deepcopy(rows)
    second[0]['metrics']['execCount'] = 3
    second[0]['metrics']['writes']['nInserted']['sum'] = 9
    second[1]['metrics']['execCount'] = 3
    second[1]['metrics']['queryExec']['docsReturned']['sum'] = 14
    if not write_first:
        rows.reverse()
        second.reverse()

    with mock.patch.object(collector, '_load_query_stats', side_effect=[rows, second]):
        assert collector._collect_metrics_rows() == []
        by_command = {row['command_type']: row for row in collector._collect_metrics_rows()}

    assert set(by_command) == {'find', 'insert'}
    assert by_command['insert']['docs_inserted_sum'] == 2
    assert by_command['insert']['docs_returned_sum'] == 0
    assert by_command['find']['docs_inserted_sum'] == 0
    assert by_command['find']['docs_returned_sum'] == 3
