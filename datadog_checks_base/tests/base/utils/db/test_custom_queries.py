# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from .common import create_query_manager, mock_executor


class TestCustomQueries:
    def test_instance(self, aggregator):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {},
                [
                    {
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                        ],
                    },
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.foo', 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_init_config(self, aggregator):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {
                    'global_custom_queries': [
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                    ],
                },
                [{}],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.foo', 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_instance_override(self, aggregator):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {
                    'global_custom_queries': [
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                    ],
                },
                [
                    {
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']},
                        ],
                    },
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.bar', 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_global_include(self, aggregator):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {
                    'global_custom_queries': [
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                    ],
                },
                [
                    {
                        'use_global_custom_queries': 'extend',
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']},
                        ],
                    },
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.foo', 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_metric('test.bar', 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_global_exclude(self, aggregator):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {
                    'global_custom_queries': [
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                    ],
                },
                [
                    {
                        'use_global_custom_queries': False,
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']},
                        ],
                    },
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.bar', 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_deduplication(self, aggregator):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {
                    'global_custom_queries': [
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                    ],
                },
                [
                    {
                        'use_global_custom_queries': 'extend',
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                        ],
                    },
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.foo', 1, count=1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_default_name(self):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {
                    'global_custom_queries': [
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                    ],
                },
                [
                    {
                        'use_global_custom_queries': 'extend',
                        'custom_queries': [{'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']}],
                    },
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )

        with pytest.raises(ValueError, match='^field `query` for custom query #1 is required$'):
            query_manager.compile_queries()

    def test_only_custom_queries(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test.statement.foo', 'type': 'gauge', 'tags': ['override:ok']},
                    {'name': 'test.statement.baz', 'type': 'gauge', 'raw': True},
                ],
                'tags': ['test:bar'],
            },
            check=AgentCheck(
                'test',
                {
                    'global_custom_queries': [
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']},
                    ],
                },
                [
                    {
                        'only_custom_queries': True,
                        'custom_queries': [
                            {
                                'query': 'foo',
                                'columns': [{'name': 'test.custom', 'type': 'gauge'}],
                                'tags': ['test:custom'],
                            },
                        ],
                    },
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.custom', 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:custom'])
        aggregator.assert_metric(
            'test.statement.foo', count=0, metric_type=aggregator.GAUGE, tags=['override:ok', 'test:bar']
        )
        aggregator.assert_metric('test.statement.baz', count=0, metric_type=aggregator.GAUGE, tags=['test:bar'])

        aggregator.assert_all_metrics_covered()

    @pytest.mark.parametrize(
        "metric_prefix",
        [
            pytest.param(None, id='no_prefix'),
            pytest.param('custom_prefix', id='with_prefix'),
        ],
    )
    def test_metric_prefix(self, aggregator, metric_prefix):
        check = AgentCheck(
            'test',
            {
                'global_custom_queries': [
                    {
                        'metric_prefix': metric_prefix,
                        'query': 'foo',
                        'columns': [{'name': 'test.foo', 'type': 'gauge'}],
                        'tags': ['test:bar'],
                    },
                ],
            },
            [{}],
        )
        check.__NAMESPACE__ = 'test'
        query_manager = create_query_manager(
            check=check,
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        metric_name = '{}.test.foo'.format(metric_prefix) if metric_prefix else 'test.test.foo'
        aggregator.assert_metric(metric_name, 1, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()
