# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryExecutor

from .common import mock_executor

pytestmark = pytest.mark.db


def create_query_executor(*args, **kwargs):
    executor = kwargs.pop('executor', None)
    if executor is None:
        executor = mock_executor()

    check = kwargs.pop("check")

    return QueryExecutor(check, executor, args, **kwargs)


def test_multiple_query_executor_simple(aggregator):
    check = AgentCheck('test', {}, [{}])
    qe1 = QueryExecutor(
        mock_executor([[1, 2, "hello"]]),
        check,
        [
            {
                'name': 'query1',
                'query': 'select 1, 2, "hello"',
                'columns': [
                    {'name': 'test.column.1', 'type': 'gauge'},
                    {'name': 'test.column.2', 'type': 'gauge'},
                    {'name': 'column_3', 'type': 'tag'},
                ],
            }
        ],
    )
    qe2 = QueryExecutor(
        mock_executor([["2015-04-01", 1500]]),
        check,
        [
            {
                'name': 'query1',
                'query': 'select date(), column from table',
                'columns': [{'name': 'date', 'type': 'tag'}, {'name': 'test.table.column', 'type': 'count'}],
            }
        ],
    )

    qe1.compile_queries()
    qe2.compile_queries()

    qe1.execute()
    qe2.execute()

    aggregator.assert_metric(
        'test.column.1',
        1,
        metric_type=aggregator.GAUGE,
        tags=['column_3:hello'],
        hostname=None,
    )

    aggregator.assert_metric(
        'test.column.2',
        2,
        metric_type=aggregator.GAUGE,
        tags=['column_3:hello'],
        hostname=None,
    )

    aggregator.assert_metric(
        'test.table.column',
        1500,
        metric_type=aggregator.COUNT,
        tags=['date:2015-04-01'],
        hostname=None,
    )
