# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.filters import regex_exclude_clauses, regex_include_clause


@pytest.mark.unit
class TestRegexExcludeClauses:
    def test_empty_returns_empty_string(self):
        assert regex_exclude_clauses("c.relname", []) == ""

    def test_none_returns_empty_string(self):
        assert regex_exclude_clauses("c.relname", None) == ""

    def test_single_pattern(self):
        assert regex_exclude_clauses("c.relname", ["temp_.*"]) == " AND c.relname !~ %s"

    def test_multiple_patterns_each_get_own_clause(self):
        result = regex_exclude_clauses("nspname", ["pg_temp_.*", "_partitions$"])
        assert result == " AND nspname !~ %s AND nspname !~ %s"

    def test_pattern_value_does_not_appear_in_sql(self):
        """Helper produces only placeholders; pattern values flow as separate cursor.execute params."""
        assert regex_exclude_clauses("c.relname", ["^p[0-9]+$"]) == " AND c.relname !~ %s"

    def test_different_columns(self):
        assert regex_exclude_clauses("datname", ["dogs_[345]"]) == " AND datname !~ %s"


@pytest.mark.unit
class TestRegexIncludeClause:
    def test_empty_returns_empty_string(self):
        assert regex_include_clause("c.relname", []) == ""

    def test_none_returns_empty_string(self):
        assert regex_include_clause("c.relname", None) == ""

    def test_single_pattern_still_wrapped_in_parens(self):
        assert regex_include_clause("c.relname", ["users.*"]) == " AND (c.relname ~ %s)"

    def test_multiple_patterns_or_joined(self):
        result = regex_include_clause("nspname", ["^app_.*", "^reports$"])
        assert result == " AND (nspname ~ %s OR nspname ~ %s)"

    def test_pattern_value_does_not_appear_in_sql(self):
        """Helper produces only placeholders; pattern values flow as separate cursor.execute params."""
        assert regex_include_clause("c.relname", ["^p[0-9]+$"]) == " AND (c.relname ~ %s)"

    def test_different_columns(self):
        assert regex_include_clause("datname", ["^prod_"]) == " AND (datname ~ %s)"
