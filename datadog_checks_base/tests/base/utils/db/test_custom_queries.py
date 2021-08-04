# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from .common import create_query_manager, mock_executor

pytestmark = pytest.mark.db


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
