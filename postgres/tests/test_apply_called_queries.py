# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.unit]


def test_apply_called_queries_base_case(pg_instance, integration_check):
    check = integration_check(pg_instance)

    rows = [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
    ]

    rows = check.statement_metrics._apply_called_queries(rows)

    assert rows == [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
    ]


def test_apply_called_queries_multiple_runs(pg_instance, integration_check):
    check = integration_check(pg_instance)

    rows = [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
    ]

    rows = check.statement_metrics._apply_called_queries(rows)

    second_rows = [
        {'queryid': 2, 'query_signature': 'abc', 'calls': 3, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
    ]
    rows = check.statement_metrics._apply_called_queries(second_rows)

    assert rows == [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 3, 'query': 'query 123', 'datname': 'db', 'rolname': 'user'},
    ]


def test_apply_called_queries_multiple_dbs(pg_instance, integration_check):
    check = integration_check(pg_instance)

    db1 = 'db1'
    db2 = 'db2'
    user1 = 'usr1'
    user2 = 'usr2'
    rows = [
        {'queryid': 2, 'query_signature': 'abc', 'calls': 3, 'query': 'query 123', 'datname': db1, 'rolname': user1},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 100, 'query': 'query 123', 'datname': db2, 'rolname': user2},
    ]
    applied = check.statement_metrics._apply_called_queries(rows)

    # The rows should remain separate because they have separate database and user values.
    assert applied == [
        {'queryid': 2, 'query_signature': 'abc', 'calls': 3, 'query': 'query 123', 'datname': db1, 'rolname': user1},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 100, 'query': 'query 123', 'datname': db2, 'rolname': user2},
    ]
