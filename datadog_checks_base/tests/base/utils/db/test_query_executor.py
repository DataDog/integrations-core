# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryExecutor

from .common import mock_executor

pytestmark = pytest.mark.db


class TestQueryExecutor:
    def test_multiple_query_executor_simple(self, aggregator):
        """Tests running multiple query executors with the same AgentCheck"""
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
            hostname='agent1',
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
            hostname='agent2',
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
            hostname='agent1',
        )

        aggregator.assert_metric(
            'test.column.2',
            2,
            metric_type=aggregator.GAUGE,
            tags=['column_3:hello'],
            hostname='agent1',
        )

        aggregator.assert_metric(
            'test.table.column',
            1500,
            metric_type=aggregator.COUNT,
            tags=['date:2015-04-01'],
            hostname='agent2',
        )

    def test_many_queries(self, aggregator):
        """Test running many unique queries"""
        num_queries = 99
        queries = []
        rows = []
        tags = ['duplicate_tag'] * 80

        for i in range(num_queries):
            queries.append(
                {
                    'name': 'query{}'.format(i),
                    'query': 'select 1',
                    'columns': [{'name': 'test.metric.{}'.format(i), 'type': 'gauge'}],
                }
            )
            rows.append([i])

        check = AgentCheck('test', {}, [{}])
        qe = QueryExecutor(mock_executor(rows), check, queries, tags=tags)
        qe.compile_queries()
        qe.execute()

        for i in range(num_queries):
            aggregator.assert_metric('test.metric.{}'.format(i), i, metric_type=aggregator.GAUGE, tags=tags)
