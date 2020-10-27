# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.base.utils.db.statement_metrics import StatementMetrics, apply_row_limits


def add_to_dict(a, b):
    a = copy.copy(a)
    for k, v in b.items():
        a[k] += v
    return a


class TestStatementMetrics:
    @pytest.mark.parametrize(
        'fn_args',
        [
            ([], [], lambda x: x),
            ([], ['a', 'b', 'c'], lambda x: x),
            ([{}, {}, {}], [], lambda x: x.get('key')),
        ],
    )
    def test_compute_derivative_rows_boundary_cases(self, fn_args):
        sm = StatementMetrics()
        sm.compute_derivative_rows(*fn_args)
        sm.compute_derivative_rows(*fn_args)

    def test_compute_derivative_rows_happy_path(self):
        sm = StatementMetrics()

        rows1 = [
            {'count': 13, 'time': 2005, 'errors': 1, 'query': 'COMMIT', 'db': 'puppies', 'user': 'dog'},
            {'count': 25, 'time': 105, 'errors': 0, 'query': 'ROLLBACK', 'db': 'puppies', 'user': 'dog'},
            {'count': 1, 'time': 10005, 'errors': 0, 'query': 'select * from kennel', 'db': 'puppies', 'user': 'rover'},
            {
                'count': 99991882777665555,
                'time': 10005,
                'errors': 0,
                'query': 'update kennel set breed="dalmatian" where id = ?',
                'db': 'puppies',
                'user': 'rover',
            },
        ]

        def key(row):
            return (row['query'], row['db'], row['user'])

        metrics = ['count', 'time']

        assert [] == sm.compute_derivative_rows(rows1, metrics, key=key)
        # No changes should produce no rows
        assert [] == sm.compute_derivative_rows(rows1, metrics, key=key)

        rows2 = [
            {'count': 1, 'time': 1, 'errors': 1, 'query': 'SELECT CURRENT_TIME', 'db': 'puppies', 'user': 'dog'},
            add_to_dict(rows1[0], {'count': 0, 'time': 0, 'errors': 15}),
            add_to_dict(rows1[1], {'count': 1, 'time': 15, 'errors': 0}),
            add_to_dict(rows1[2], {'count': 20, 'time': 900, 'errors': 0}),
            add_to_dict(rows1[3], {'count': 7, 'time': 0.5, 'errors': 0}),
        ]
        expected = [
            # First row only incremented 'errors' which is not a tracked metric, so it is omitted from the output
            {'count': 1, 'time': 15, 'errors': 0, 'query': 'ROLLBACK', 'db': 'puppies', 'user': 'dog'},
            {'count': 20, 'time': 900, 'errors': 0, 'query': 'select * from kennel', 'db': 'puppies', 'user': 'rover'},
            {
                'count': 7,
                'time': 0.5,
                'errors': 0,
                'query': 'update kennel set breed="dalmatian" where id = ?',
                'db': 'puppies',
                'user': 'rover',
            },
        ]
        assert expected == sm.compute_derivative_rows(rows2, metrics, key=key)
        # No changes should produce no rows
        assert [] == sm.compute_derivative_rows(rows2, metrics, key=key)

    def test_compute_derivative_rows_stats_reset(self):
        sm = StatementMetrics()

        def key(row):
            return (row['query'], row['db'], row['user'])

        metrics = ['count', 'time']

        rows1 = [
            {'count': 13, 'time': 2005, 'errors': 1, 'query': 'COMMIT', 'db': 'puppies', 'user': 'dog'},
            {'count': 25, 'time': 105, 'errors': 0, 'query': 'ROLLBACK', 'db': 'puppies', 'user': 'dog'},
        ]
        rows2 = [
            add_to_dict(rows1[0], {'count': 0, 'time': 1, 'errors': 15}),
            add_to_dict(rows1[1], {'count': 1, 'time': 15, 'errors': 0}),
        ]
        # Simulate a stats reset by decreasing one of the metrics rather than increasing
        rows3 = [
            add_to_dict(rows2[1], {'count': 1, 'time': 15, 'errors': 0}),
            add_to_dict(rows2[0], {'count': -1, 'time': 0, 'errors': 15}),
        ]
        rows4 = [
            add_to_dict(rows3[1], {'count': 1, 'time': 1, 'errors': 0}),
            add_to_dict(rows3[0], {'count': 1, 'time': 1, 'errors': 1}),
        ]
        assert [] == sm.compute_derivative_rows(rows1, metrics, key=key)
        assert 2 == len(sm.compute_derivative_rows(rows2, metrics, key=key))
        assert [] == sm.compute_derivative_rows(rows3, metrics, key=key)
        assert 2 == len(sm.compute_derivative_rows(rows4, metrics, key=key))

    def test_apply_row_limits(self):
        def assert_any_order(a, b):
            assert sorted(a, key=lambda row: row['_']) == sorted(b, key=lambda row: row['_'])

        rows = [
            {'_': 0, 'count': 2, 'time': 1000},
            {'_': 1, 'count': 20, 'time': 5000},
            {'_': 2, 'count': 20, 'time': 8000},
            {'_': 3, 'count': 180, 'time': 8000},
            {'_': 4, 'count': 0, 'time': 10},
            {'_': 5, 'count': 60, 'time': 500},
            {'_': 6, 'count': 90, 'time': 5000},
            {'_': 7, 'count': 50, 'time': 5000},
            {'_': 8, 'count': 40, 'time': 100},
            {'_': 9, 'count': 30, 'time': 900},
            {'_': 10, 'count': 80, 'time': 800},
            {'_': 11, 'count': 110, 'time': 7000},
        ]
        assert_any_order(
            [], apply_row_limits(rows, {'count': (0, 0), 'time': (0, 0)}, 'count', True, key=lambda row: row['_'])
        )

        expected = [
            {'_': 3, 'count': 180, 'time': 8000},
            {'_': 4, 'count': 0, 'time': 10},  # The bottom 1 row for both 'count' and 'time'
            {'_': 2, 'count': 20, 'time': 8000},
        ]
        assert_any_order(
            expected, apply_row_limits(rows, {'count': (1, 1), 'time': (1, 1)}, 'count', True, key=lambda row: row['_'])
        )

        expected = [
            {'_': 5, 'count': 60, 'time': 500},
            {'_': 10, 'count': 80, 'time': 800},
            {'_': 6, 'count': 90, 'time': 5000},
            {'_': 11, 'count': 110, 'time': 7000},
            {'_': 3, 'count': 180, 'time': 8000},
            {'_': 4, 'count': 0, 'time': 10},
            {'_': 0, 'count': 2, 'time': 1000},
            {'_': 2, 'count': 20, 'time': 8000},
            {'_': 8, 'count': 40, 'time': 100},
        ]
        assert_any_order(
            expected, apply_row_limits(rows, {'count': (5, 2), 'time': (2, 2)}, 'count', True, key=lambda row: row['_'])
        )

        assert_any_order(
            rows,
            apply_row_limits(rows, {'count': (6, 6), 'time': (0, 0)}, 'time', False, key=lambda row: row['_']),
        )

        assert_any_order(
            rows,
            apply_row_limits(rows, {'count': (0, 0), 'time': (4, 8)}, 'time', False, key=lambda row: row['_']),
        )

        assert_any_order(
            rows,
            apply_row_limits(rows, {'count': (20, 20), 'time': (12, 5)}, 'time', False, key=lambda row: row['_']),
        )
