# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from datetime import datetime, timedelta

from dateutil.tz import gettz

from datadog_checks.base.utils.time import UTC

from .common import create_query_manager, mock_executor


class TestColumnTransformers:
    def test_tag_boolean(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'affirmative', 'type': 'tag', 'boolean': True},
                    {'name': 'test.foo', 'type': 'gauge'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([[1, 5], [0, 7]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'affirmative:true']
        )
        aggregator.assert_metric(
            'test.foo', 7, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'affirmative:false']
        )
        aggregator.assert_all_metrics_covered()

    def test_tag_list(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'foo_tag', 'type': 'tag_list'},
                    {'name': 'test.foo', 'type': 'gauge'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor(
                [['tag1', ['tagA', 'tagB'], 5], ['tag2', 'tagC, tagD', 7], ['tag3', 'tagE,tagF', 9]]
            ),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo',
            5,
            metric_type=aggregator.GAUGE,
            tags=['test:foo', 'test:bar', 'test:tag1', 'foo_tag:tagA', 'foo_tag:tagB'],
        )
        aggregator.assert_metric(
            'test.foo',
            7,
            metric_type=aggregator.GAUGE,
            tags=['test:foo', 'test:bar', 'test:tag2', 'foo_tag:tagC', 'foo_tag:tagD'],
        )
        aggregator.assert_metric(
            'test.foo',
            9,
            metric_type=aggregator.GAUGE,
            tags=['test:foo', 'test:bar', 'test:tag3', 'foo_tag:tagE', 'foo_tag:tagF'],
        )
        aggregator.assert_all_metrics_covered()

    def test_monotonic_gauge(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'monotonic_gauge'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 5], ['tag2', 7]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo.total', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'test.foo.count', 5, metric_type=aggregator.MONOTONIC_COUNT, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'test.foo.total', 7, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag2']
        )
        aggregator.assert_metric(
            'test.foo.count', 7, metric_type=aggregator.MONOTONIC_COUNT, tags=['test:foo', 'test:bar', 'test:tag2']
        )
        aggregator.assert_all_metrics_covered()

    def test_temporal_percent_named(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'temporal_percent', 'scale': 'second'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 5]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 500, metric_type=aggregator.RATE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_temporal_percent_int(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'temporal_percent', 'scale': 1},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 5]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 500, metric_type=aggregator.RATE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_temporal_percent_cast_to_float(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'temporal_percent', 'scale': 1},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', '5.2']]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 520, metric_type=aggregator.RATE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_match_global(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {
                        'name': 'columnar',
                        'type': 'match',
                        'items': {
                            'global': {'name': 'test.global', 'type': 'gauge'},
                            'local': {'name': 'test.local', 'type': 'gauge'},
                        },
                        'source': 'test1',
                    },
                    {'name': 'test1', 'type': 'source'},
                    {'name': 'test2', 'type': 'source'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['global', 5, 7]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.global', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_match_local(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {
                        'name': 'columnar',
                        'type': 'match',
                        'items': {
                            'global': {'name': 'test.global', 'type': 'gauge'},
                            'local': {'name': 'test.local', 'type': 'gauge', 'source': 'test2'},
                        },
                        'source': 'test1',
                    },
                    {'name': 'test1', 'type': 'source'},
                    {'name': 'test2', 'type': 'source'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['local', 5, 7]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.local', 7, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_match_none(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {
                        'name': 'columnar',
                        'type': 'match',
                        'items': {
                            'global': {'name': 'test.global', 'type': 'gauge'},
                            'local': {'name': 'test.local', 'type': 'gauge', 'source': 'test2'},
                        },
                        'source': 'test1',
                    },
                    {'name': 'test1', 'type': 'source'},
                    {'name': 'test2', 'type': 'source'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['nonlocal', 5, 7]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_all_metrics_covered()

    def test_service_check_known(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test.foo', 'type': 'service_check', 'status_map': {'known': 'ok'}},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['known']]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_service_check('test.foo', 0, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_service_check_unknown(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test.foo', 'type': 'service_check', 'status_map': {'known': 'ok'}, 'message': 'baz'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['unknown']]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_service_check('test.foo', 3, message='baz', tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_service_check_unknown_with_message_from_source(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'message_source', 'type': 'source'},
                    {
                        'name': 'test.foo',
                        'type': 'service_check',
                        'status_map': {'known': 'ok'},
                        'message': 'failed due to {message_source}',
                    },
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['crash', 'unknown']]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_service_check('test.foo', 3, message='failed due to crash', tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_time_elapsed_native(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'time_elapsed', 'format': 'native'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', datetime.now(UTC) + timedelta(hours=-1)]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        assert 'test.foo' in aggregator._metrics
        assert len(aggregator._metrics) == 1
        assert len(aggregator._metrics['test.foo']) == 1
        m = aggregator._metrics['test.foo'][0]

        assert 3599 < m.value < 3601
        assert m.type == aggregator.GAUGE
        assert m.tags == ['test:foo', 'test:bar', 'test:tag1']

    def test_time_elapsed_native_default(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'time_elapsed'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', datetime.now(UTC) + timedelta(hours=-1)]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        assert 'test.foo' in aggregator._metrics
        assert len(aggregator._metrics) == 1
        assert len(aggregator._metrics['test.foo']) == 1
        m = aggregator._metrics['test.foo'][0]

        assert 3599 < m.value < 3601
        assert m.type == aggregator.GAUGE
        assert m.tags == ['test:foo', 'test:bar', 'test:tag1']

    def test_time_elapsed_unix_time(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'time_elapsed', 'format': 'unix_time'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', time.time() - 3600]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        assert 'test.foo' in aggregator._metrics
        assert len(aggregator._metrics) == 1
        assert len(aggregator._metrics['test.foo']) == 1
        m = aggregator._metrics['test.foo'][0]

        assert 3599 < m.value < 3601
        assert m.type == aggregator.GAUGE
        assert m.tags == ['test:foo', 'test:bar', 'test:tag1']

    def test_time_elapsed_format(self, aggregator):
        time_format = '%Y-%m-%dT%H-%M-%S%Z'
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'time_elapsed', 'format': time_format},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', (datetime.now(UTC) + timedelta(hours=-1)).strftime(time_format)]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        assert 'test.foo' in aggregator._metrics
        assert len(aggregator._metrics) == 1
        assert len(aggregator._metrics['test.foo']) == 1
        m = aggregator._metrics['test.foo'][0]

        assert abs(m.value - 3600) < 2
        assert m.type == aggregator.GAUGE
        assert m.tags == ['test:foo', 'test:bar', 'test:tag1']

    def test_time_elapsed_datetime_naive(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'time_elapsed', 'format': 'native'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', datetime.utcnow() + timedelta(hours=-1)]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        assert 'test.foo' in aggregator._metrics
        assert len(aggregator._metrics) == 1
        assert len(aggregator._metrics['test.foo']) == 1
        m = aggregator._metrics['test.foo'][0]

        assert 3599 < m.value < 3601
        assert m.type == aggregator.GAUGE
        assert m.tags == ['test:foo', 'test:bar', 'test:tag1']

    def test_time_elapsed_datetime_aware(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.foo', 'type': 'time_elapsed', 'format': 'native'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', datetime.now(gettz('EST')) + timedelta(hours=-1)]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        assert 'test.foo' in aggregator._metrics
        assert len(aggregator._metrics) == 1
        assert len(aggregator._metrics['test.foo']) == 1
        m = aggregator._metrics['test.foo'][0]

        assert 3599 < m.value < 3601
        assert m.type == aggregator.GAUGE
        assert m.tags == ['test:foo', 'test:bar', 'test:tag1']


class TestExtraTransformers:
    def test_expression(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'gauge'}],
                'extras': [
                    {'name': 'divide', 'type': 'expression', 'expression': 'test.foo / 2', 'submit_type': 'gauge'}
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 5]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'divide', 2.5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_expression_detect_type(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'gauge'}],
                'extras': [{'name': 'divide', 'expression': 'test.foo / 2', 'submit_type': 'gauge'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 5]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'divide', 2.5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_expression_verbose(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'gauge'}],
                'extras': [
                    {'name': 'divide', 'expression': 'SOURCES["test.foo"] / 2', 'verbose': True, 'submit_type': 'gauge'}
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 5]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'divide', 2.5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_expression_store_source(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'gauge'}],
                'extras': [
                    {'name': 'src', 'expression': '2 ** 3'},
                    {'name': 'src.cube', 'type': 'gauge', 'source': 'src'},
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 5]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'src.cube', 8, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_expression_pass_modifiers(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'gauge'}],
                'extras': [
                    {
                        'name': 'temp.pct',
                        'expression': 'test.foo / 2',
                        'submit_type': 'temporal_percent',
                        'scale': 'second',
                    }
                ],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 10]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 10, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'temp.pct', 500, metric_type=aggregator.RATE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()

    def test_percent(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test', 'type': 'tag'},
                    {'name': 'test.part', 'type': 'gauge'},
                    {'name': 'test.total', 'type': 'gauge'},
                ],
                'extras': [{'name': 'percent', 'type': 'percent', 'part': 'test.part', 'total': 'test.total'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['tag1', 3, 5]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.part', 3, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'test.total', 5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_metric(
            'percent', 60, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1']
        )
        aggregator.assert_all_metrics_covered()
