# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryExecutor

from .common import mock_executor


class TestQueryExecutor:
    def test_all_column_types(self, aggregator):
        """Tests the exhaustive list of all metric types"""
        queries = []
        rows_first_run = []
        rows_second_run = []
        shared_tags = ['app:opa', 'ap-west']
        tag_list = ("t1", "t2", "t3")

        queries.append(
            {
                'name': 'q1',
                'query': 'select gauge, count, monotonic_count, rate, histogram, historate, tag, taglist from mytable',
                'columns': [
                    {'name': 'metric.gauge', 'type': 'gauge'},
                    {'name': 'metric.count', 'type': 'count'},
                    {'name': 'metric.monotonic_count', 'type': 'monotonic_count'},
                    {'name': 'metric.rate', 'type': 'rate'},
                    {'name': 'metric.histogram', 'type': 'histogram'},
                    {'name': 'metric.historate', 'type': 'historate'},
                    {'name': 'tagcol', 'type': 'tag'},
                    {'name': 'taglist', 'type': 'tag_list'},
                ],
            }
        )
        rows_first_run.extend([[1, 1, 1, 1, 1, 1, "dog", tag_list], [0, 2, 4, 8, 16, 32, "dog", tag_list]])
        rows_second_run.extend(
            [
                [-1, -1, -1, -1, -1, -1, "dog", tag_list],
            ]
        )

        expected_tags = shared_tags + ['tagcol:dog'] + ['taglist:t1', 'taglist:t2', 'taglist:t3']

        check = AgentCheck('test', {}, [{}])
        qe = QueryExecutor(mock_executor(rows_first_run), check, queries=queries, tags=shared_tags)
        qe.compile_queries()
        qe.execute()

        aggregator.assert_metric('metric.gauge', 0, tags=expected_tags)
        aggregator.assert_metric('metric.count', 3, tags=expected_tags)
        aggregator.assert_metric('metric.monotonic_count', 4, tags=expected_tags)
        aggregator.assert_metric('metric.rate', 8, tags=expected_tags)
        aggregator.assert_metric('metric.histogram', 16, tags=expected_tags)
        aggregator.assert_metric('metric.historate', 32, tags=expected_tags)
        aggregator.assert_all_metrics_covered()

        qe.executor = mock_executor(rows_second_run)
        qe.execute()

        aggregator.assert_metric('metric.gauge', -1, tags=expected_tags)
        aggregator.assert_metric('metric.count', 2, tags=expected_tags)
        aggregator.assert_metric('metric.monotonic_count', 4, tags=expected_tags)
        aggregator.assert_metric('metric.rate', -1, tags=expected_tags)
        aggregator.assert_metric('metric.histogram', -1, tags=expected_tags)
        aggregator.assert_metric('metric.historate', -1, tags=expected_tags)
        aggregator.assert_all_metrics_covered()

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
        """Test running many unique queries in a single executor"""
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

    def test_query_with_collection_interval(self, aggregator):
        """Test running a query with a custom collection interval"""
        collection_interval = 1
        queries = [
            {
                'name': 'query1',
                'query': 'select 1',
                'columns': [{'name': 'test.metric_with_interval', 'type': 'gauge'}],
                'collection_interval': collection_interval,
            }
        ]

        check = AgentCheck('test', {}, [{}])
        qe = QueryExecutor(mock_executor([[1]]), check, queries)

        qe.compile_queries()

        qe.execute()  # First run, should emit a metric
        time.sleep(0.5 * collection_interval)  # Sleep for less than the collection interval
        qe.execute()  # Second run, should not emit a metric because the interval hasn't passed
        time.sleep(0.5 * collection_interval)
        qe.execute()  # Third run, should emit a metric

        aggregator.assert_metric('test.metric_with_interval', 1, metric_type=aggregator.GAUGE)
        assert len(aggregator.metrics('test.metric_with_interval')) == 2

        # Reset the aggregator and re-compile query executor
        aggregator.reset()
        qe.compile_queries()
        qe.execute()  # Forth run, re-compile should not reset the last execution time
        aggregator.assert_metric('test.metric_with_interval', count=0)
        time.sleep(collection_interval)
        qe.execute()  # Fifth run, should emit a metric
        aggregator.assert_metric('test.metric_with_interval', 1, metric_type=aggregator.GAUGE)
        assert len(aggregator.metrics('test.metric_with_interval')) == 1

    @pytest.mark.parametrize(
        'collection_interval, expected_exception',
        [
            pytest.param(0.5, ValueError, id='invalid interval 0.5s'),  # 0.5s is invalid because it rounds to 0
            pytest.param(0, ValueError, id='invalid interval 0s'),
            pytest.param(-1, ValueError, id='invalid interval -1s'),
            pytest.param('test', ValueError, id='invalid interval not a number'),
        ],
    )
    def test_query_with_collection_interval_with_exception(self, collection_interval, expected_exception):
        """Test running a query with a custom collection interval"""
        queries = [
            {
                'name': 'query1',
                'query': 'select 1',
                'columns': [{'name': 'test.metric_with_interval', 'type': 'gauge'}],
                'collection_interval': collection_interval,
            }
        ]

        check = AgentCheck('test', {}, [{}])
        qe = QueryExecutor(mock_executor([[1]]), check, queries)

        with pytest.raises(expected_exception):
            qe.compile_queries()

    @pytest.mark.parametrize(
        "metric_prefix",
        [
            pytest.param(None, id='no_prefix'),
            pytest.param('custom_prefix', id='custom_prefix'),
        ],
    )
    def test_query_with_metric_prefix(self, aggregator, metric_prefix):
        queries = [
            {
                'metric_prefix': metric_prefix,
                'name': 'query1',
                'query': 'select 1',
                'columns': [{'name': 'metric', 'type': 'gauge'}],
            }
        ]

        check = AgentCheck('test', {}, [{}])
        check.__NAMESPACE__ = 'test_check'
        qe = QueryExecutor(mock_executor([[1]]), check, queries)
        qe.compile_queries()
        qe.execute()

        metric_name = '{}.metric'.format(metric_prefix) if metric_prefix else 'test_check.metric'
        aggregator.assert_metric(metric_name, 1, metric_type=aggregator.GAUGE)

    @pytest.mark.parametrize(
        "metric_prefix,expected_exception",
        [
            pytest.param(123, ValueError, id='invalid prefix not a string'),
            pytest.param('', ValueError, id='empty prefix'),
        ],
    )
    def test_query_with_metric_prefix_with_exception(self, metric_prefix, expected_exception):
        queries = [
            {
                'metric_prefix': metric_prefix,
                'name': 'query1',
                'query': 'select 1',
                'columns': [{'name': 'metric', 'type': 'gauge'}],
            }
        ]

        check = AgentCheck('test', {}, [{}])
        check.__NAMESPACE__ = 'test_check'
        qe = QueryExecutor(mock_executor([[1]]), check, queries)

        with pytest.raises(expected_exception):
            qe.compile_queries()
