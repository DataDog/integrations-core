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

    def test_null_query_is_logged_without_an_embedded_null(self):
        with (
            mock.patch(
                'datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata',
                side_effect=ValueError('embedded null character'),
            ),
            mock.patch('datadog_checks.base.utils.db.query_metrics.obfuscation.logger.warning') as warning,
        ):
            assert obfuscate_statement("SELECT 'abc\x00def'", '{}', log_unobfuscated_queries=True) is None

        for arg in warning.call_args[0]:
            if isinstance(arg, str):
                assert '\x00' not in arg

    def test_identical_text_yields_identical_signature(self):
        """Callers that cannot cache still get signatures consistent with the cached path."""
        first = obfuscate_statement('SELECT 1', '{}')
        second = obfuscate_statement('SELECT 1', '{}')
        assert first.query_signature == second.query_signature
