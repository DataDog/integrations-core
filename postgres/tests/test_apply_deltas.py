# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.unit]


def test_apply_deltas_base_case(pg_instance, integration_check):
    check = integration_check(pg_instance)

    rows = [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2},
    ]
    metrics = ['calls']

    rows = check.statement_metrics._apply_deltas(rows, metrics)

    assert len(rows) == 1
    assert rows[0] == {'queryid': 1, 'query_signature': 'abc', 'calls': 3}


def test_apply_deltas_multiple_runs(pg_instance, integration_check):
    check = integration_check(pg_instance)

    rows = [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2},
    ]
    metrics = ['calls']

    rows = check.statement_metrics._apply_deltas(rows, metrics)

    second_rows = [
        {'queryid': 2, 'query_signature': 'abc', 'calls': 3},
    ]
    rows = check.statement_metrics._apply_deltas(second_rows, metrics)

    assert len(rows) == 1
    assert rows[0] == {'queryid': 1, 'query_signature': 'abc', 'calls': 4}
