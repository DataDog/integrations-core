# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.base.utils.db.statement_metrics import StatementMetrics


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

        expected_by_query = {v['query']: v for v in expected}
        derived_rows = {v['query']: v for v in sm.compute_derivative_rows(rows2, metrics, key=key)}
        assert expected_by_query == derived_rows
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
            add_to_dict(rows2[0], {'count': -1, 'time': 0, 'errors': 15}),
            add_to_dict(rows2[1], {'count': 1, 'time': 15, 'errors': 0}),
        ]
        rows4 = [
            add_to_dict(rows3[0], {'count': 1, 'time': 1, 'errors': 1}),
            add_to_dict(rows3[1], {'count': 1, 'time': 1, 'errors': 0}),
        ]
        assert [] == sm.compute_derivative_rows(rows1, metrics, key=key)
        assert 2 == len(sm.compute_derivative_rows(rows2, metrics, key=key))  # both rows computed
        assert 1 == len(sm.compute_derivative_rows(rows3, metrics, key=key))  # only 1 row computed
        assert 2 == len(sm.compute_derivative_rows(rows4, metrics, key=key))  # both rows computed

    def test_compute_derivative_rows_with_duplicates(self):
        sm = StatementMetrics()

        def key(row):
            return (row['query_signature'], row['db'], row['user'])

        metrics = ['count', 'time']

        rows1 = [
            {
                'count': 13,
                'time': 2005,
                'errors': 1,
                'query': 'SELECT * FROM table1 where id = ANY(?)',
                'query_signature': 'sig1',
                'db': 'puppies',
                'user': 'dog',
            },
            {
                'count': 25,
                'time': 105,
                'errors': 0,
                'query': 'SELECT * FROM table1 where id = ANY(?, ?)',
                'query_signature': 'sig1',
                'db': 'puppies',
                'user': 'dog',
            },
        ]

        rows2 = [
            {
                'count': 14,
                'time': 2006,
                'errors': 32,
                'query': 'SELECT * FROM table1 where id = ANY(?)',
                'query_signature': 'sig1',
                'db': 'puppies',
                'user': 'dog',
            },
            {
                'count': 26,
                'time': 125,
                'errors': 1,
                'query': 'SELECT * FROM table1 where id = ANY(?, ?)',
                'query_signature': 'sig1',
                'db': 'puppies',
                'user': 'dog',
            },
        ]

        # Run a first check to initialize tracking
        sm.compute_derivative_rows(rows1, metrics, key=key)
        # Run the check again to compute the metrics
        metrics = sm.compute_derivative_rows(rows2, metrics, key=key)

        expected_merged_metrics = [
            {
                'count': 2,
                'time': 21,
                'errors': 32,
                'db': 'puppies',
                'query': 'SELECT * FROM table1 where id = ANY(?)',
                'query_signature': 'sig1',
                'user': 'dog',
            }
        ]

        assert expected_merged_metrics == metrics
