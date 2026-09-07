# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for obfuscate_statement."""

from unittest import mock

from datadog_checks.base.utils.db.query_metrics import obfuscate_statement


class TestObfuscateStatement:
    def test_returns_result_with_signature(self):
        result = obfuscate_statement('SELECT 1', '{}')
        assert result is not None
        assert result.obfuscated_query
        assert result.query_signature

    def test_returns_none_when_obfuscation_fails(self):
        with mock.patch(
            'datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata',
            side_effect=RuntimeError('cannot obfuscate'),
        ):
            assert obfuscate_statement('SELECT 1', '{}') is None

    def test_identical_text_yields_identical_signature(self):
        """Callers that cannot cache still get signatures consistent with the cached path."""
        first = obfuscate_statement('SELECT 1', '{}')
        second = obfuscate_statement('SELECT 1', '{}')
        assert first.query_signature == second.query_signature
