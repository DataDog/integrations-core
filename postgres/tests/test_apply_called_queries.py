# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.unit]


def test_apply_called_queries_base_case(pg_instance, integration_check):
    check = integration_check(pg_instance)

    rows = [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2, 'query': 'query 123'},
    ]

    rows = check.statement_metrics._apply_called_queries(rows)

    assert rows == [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2, 'query': 'query 123'},
    ]


def test_apply_called_queries_multiple_runs(pg_instance, integration_check):
    check = integration_check(pg_instance)

    rows = [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2, 'query': 'query 123'},
    ]

    rows = check.statement_metrics._apply_called_queries(rows)

    second_rows = [
        {'queryid': 2, 'query_signature': 'abc', 'calls': 3, 'query': 'query 123'},
    ]
    rows = check.statement_metrics._apply_called_queries(second_rows)

    assert rows == [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 3, 'query': 'query 123'},
    ]
