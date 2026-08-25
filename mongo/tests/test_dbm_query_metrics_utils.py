# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

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
