# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.unit]


def test_apply_deltas(pg_instance, integration_check):
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)

    rows = [
        {'queryid': 1, 'query_signature': 'abc', 'calls': 1},
        {'queryid': 2, 'query_signature': 'abc', 'calls': 2},
    ]
    metrics = ['calls']

    rows = check.statement_metrics._apply_deltas(rows, metrics)

    assert len(rows) == 1
    assert rows[0] == {'queryid': 1, 'query_signature': 'abc', 'calls': 3}
