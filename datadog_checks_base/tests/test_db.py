# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db import Query, QueryManager

pytestmark = pytest.mark.db


def mock_executor(result=()):
    def executor(_):
        return result

    return executor


def create_query_manager(*args, **kwargs):
    executor = kwargs.pop('executor', None)
    if executor is None:
        executor = mock_executor()

    check = kwargs.pop('check', None) or AgentCheck('test', {}, [{}])
    return QueryManager(check, executor, [Query(arg) for arg in args], **kwargs)


class TestQueryResultIteration:
    def test_executor_empty_result(self):
        query_manager = create_query_manager()

        assert list(query_manager.execute_query('foo')) == []

    def test_executor_no_result(self):
        query_manager = create_query_manager(executor=mock_executor(None))

        assert list(query_manager.execute_query('foo')) == []

    def test_executor_trigger_result(self):
        class Result(object):
            def __init__(self, _):
                pass

            def __iter__(self):
                raise ValueError('no result set')

        query_manager = create_query_manager(executor=Result)

        with pytest.raises(ValueError, match='^no result set$'):
            query_manager.execute_query('foo')

    def test_executor_expected_result(self):
        query_manager = create_query_manager(executor=mock_executor([[0, 1], [1, 2], [2, 3]]))

        assert list(query_manager.execute_query('foo')) == [[0, 1], [1, 2], [2, 3]]

    def test_executor_expected_result_generator(self):
        class Result(object):
            def __init__(self, _):
                pass

            def __iter__(self):
                for i in range(3):
                    yield [i, i + 1]

        query_manager = create_query_manager(executor=Result)

        assert list(query_manager.execute_query('foo')) == [[0, 1], [1, 2], [2, 3]]


class TestQueryCompilation:
    def test_no_query_name(self):
        query_manager = create_query_manager({})

        with pytest.raises(ValueError, match='^query field `name` is required$'):
            query_manager.compile_queries()

    def test_query_name_not_string(self):
        query_manager = create_query_manager({'name': 5})

        with pytest.raises(ValueError, match='^query field `name` must be a string$'):
            query_manager.compile_queries()

    def test_no_query(self):
        query_manager = create_query_manager({'name': 'test query'})

        with pytest.raises(ValueError, match='^field `query` for test query is required$'):
            query_manager.compile_queries()

    def test_query_not_string(self):
        query_manager = create_query_manager({'name': 'test query', 'query': 5})

        with pytest.raises(ValueError, match='^field `query` for test query must be a string$'):
            query_manager.compile_queries()

    def test_no_columns(self):
        query_manager = create_query_manager({'name': 'test query', 'query': 'foo'})

        with pytest.raises(ValueError, match='^field `columns` for test query is required$'):
            query_manager.compile_queries()

    def test_columns_not_list(self):
        query_manager = create_query_manager({'name': 'test query', 'query': 'foo', 'columns': 'bar'})

        with pytest.raises(ValueError, match='^field `columns` for test query must be a list$'):
            query_manager.compile_queries()

    def test_tags_not_list(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [{}], 'tags': 'test:bar'}
        )

        with pytest.raises(ValueError, match='^field `tags` for test query must be a list$'):
            query_manager.compile_queries()

    def test_column_not_dict(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [['column']], 'tags': ['test:bar']}
        )

        with pytest.raises(ValueError, match='^column #1 of test query is not a mapping$'):
            query_manager.compile_queries()

    def test_column_no_name(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [{}, {'foo': 'bar'}], 'tags': ['test:bar']}
        )

        with pytest.raises(ValueError, match='^field `name` for column #2 of test query is required$'):
            query_manager.compile_queries()

    def test_column_name_not_string(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [{'name': 5}], 'tags': ['test:bar']}
        )

        with pytest.raises(ValueError, match='^field `name` for column #1 of test query must be a string$'):
            query_manager.compile_queries()

    def test_column_no_type(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [{'name': 'test.foo'}], 'tags': ['test:bar']}
        )

        with pytest.raises(ValueError, match='^field `type` for column test.foo of test query is required$'):
            query_manager.compile_queries()

    def test_column_type_not_string(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 5}], 'tags': ['test:bar']}
        )

        with pytest.raises(ValueError, match='^field `type` for column test.foo of test query must be a string$'):
            query_manager.compile_queries()

    def test_column_type_source_ok(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'tags': ['test:bar'],
            }
        )

        query_manager.compile_queries()

    def test_column_type_unknown(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'something'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^unknown type `something` for column test.foo of test query$'):
            query_manager.compile_queries()

    def test_compilation_idempotent(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [{}], 'tags': ['test:bar']}
        )

        query_manager.compile_queries()
        query_manager.compile_queries()


class TestTransformerCompilation:
    def test_temporal_percent_no_scale(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'temporal_percent'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `temporal_percent` for column test.foo of test query: '
                'the `scale` parameter is required$'
            ),
        ):
            query_manager.compile_queries()

    def test_temporal_percent_unknown_scale(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'temporal_percent', 'scale': 'bar'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `temporal_percent` for column test.foo of test query: '
                'the `scale` parameter must be one of: '
            ),
        ):
            query_manager.compile_queries()

    def test_temporal_percent_scale_not_int(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'temporal_percent', 'scale': 1.23}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `temporal_percent` for column test.foo of test query: '
                'the `scale` parameter must be an integer representing parts of a second e.g. 1000 for millisecond$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_no_items(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'match'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match='^error compiling type `match` for column test.foo of test query: the `items` parameter is required$',
        ):
            query_manager.compile_queries()

    def test_match_items_not_dict(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'match', 'items': []}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'the `items` parameter must be a mapping$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_item_not_dict(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'match', 'items': {'foo': 'bar'}}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match='^error compiling type `match` for column test.foo of test query: item `foo` is not a mapping$',
        ):
            query_manager.compile_queries()

    def test_match_item_no_name(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'match', 'items': {'foo': {}}}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'the `name` parameter for item `foo` is required$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_item_name_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'match', 'items': {'foo': {'name': 7}}}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'the `name` parameter for item `foo` must be a string$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_item_no_type(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'match', 'items': {'foo': {'name': 'test.foo'}}}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'the `type` parameter for item `foo` is required$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_item_type_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'match', 'items': {'foo': {'name': 'test.foo', 'type': 7}}}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'the `type` parameter for item `foo` must be a string$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_item_type_unknown(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test.foo', 'type': 'match', 'items': {'foo': {'name': 'test.foo', 'type': 'unknown'}}}
                ],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'unknown type `unknown` for item `foo`$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_item_no_source(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test.foo', 'type': 'match', 'items': {'foo': {'name': 'test.foo', 'type': 'gauge'}}}
                ],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'the `source` parameter for item `foo` is required$'
            ),
        ):
            query_manager.compile_queries()

    def test_match_item_source_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {
                        'name': 'test.foo',
                        'type': 'match',
                        'items': {'foo': {'name': 'test.foo', 'type': 'gauge', 'source': 7}},
                    }
                ],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `match` for column test.foo of test query: '
                'the `source` parameter for item `foo` must be a string$'
            ),
        ):
            query_manager.compile_queries()


class TestSubmission:
    @pytest.mark.parametrize(
        'metric_type_name, metric_type_id',
        [item for item in AggregatorStub.METRIC_ENUM_MAP.items() if item[0] != 'counter'],
        ids=[metric_type for metric_type in AggregatorStub.METRIC_ENUM_MAP if metric_type != 'counter'],
    )
    def test_basic(self, metric_type_name, metric_type_id, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'level', 'type': 'tag'}, None, {'name': 'test.foo', 'type': metric_type_name}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['over', 'stuff', 9000]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo', 9000, metric_type=metric_type_id, tags=['test:foo', 'test:bar', 'level:over']
        )
        aggregator.assert_all_metrics_covered()

    def test_aggregation(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'count'}, {'name': 'tag', 'type': 'tag'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([[3, 'tag1'], [7, 'tag2'], [5, 'tag1']]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.foo', 8, metric_type=aggregator.COUNT, tags=['test:foo', 'test:bar', 'tag:tag1'])
        aggregator.assert_metric('test.foo', 7, metric_type=aggregator.COUNT, tags=['test:foo', 'test:bar', 'tag:tag2'])
        aggregator.assert_all_metrics_covered()

    def test_no_query_tags(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'count'}, {'name': 'tag', 'type': 'tag'}],
            },
            executor=mock_executor([[3, 'tag1'], [7, 'tag2'], [5, 'tag1']]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test.foo', 8, metric_type=aggregator.COUNT, tags=['test:foo', 'tag:tag1'])
        aggregator.assert_metric('test.foo', 7, metric_type=aggregator.COUNT, tags=['test:foo', 'tag:tag2'])
        aggregator.assert_all_metrics_covered()

    def test_kwarg_passing(self, aggregator):
        class MyCheck(AgentCheck):
            __NAMESPACE__ = 'test_check'

        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test.foo', 'type': 'gauge', 'tags': ['override:ok']},
                    {'name': 'test.foo', 'type': 'gauge', 'raw': True},
                ],
                'tags': ['test:bar'],
            },
            check=MyCheck('test', {}, [{}]),
            executor=mock_executor([[1, 2]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric('test_check.test.foo', 1, metric_type=aggregator.GAUGE, tags=['override:ok'])
        aggregator.assert_metric('test.foo', 2, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_query_execution_error(self, caplog, aggregator):
        class Result(object):
            def __init__(self, _):
                pass

            def __iter__(self):
                raise ValueError('no result set')

        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'gauge'}],
                'tags': ['test:bar'],
            },
            executor=Result,
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        expected_message = 'Error querying test query: no result set'
        matches = [level for _, level, message in caplog.record_tuples if message == expected_message]

        assert len(matches) == 1, 'Expected log with message: {}'.format(expected_message)
        assert matches[0] == logging.ERROR

        aggregator.assert_all_metrics_covered()

    def test_query_execution_error_with_handler(self, caplog, aggregator):
        class Result(object):
            def __init__(self, _):
                pass

            def __iter__(self):
                raise ValueError('no result set')

        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'gauge'}],
                'tags': ['test:bar'],
            },
            executor=Result,
            tags=['test:foo'],
            error_handler=lambda s: s.replace('re', 'in'),
        )
        query_manager.compile_queries()
        query_manager.execute()

        expected_message = 'Error querying test query: no insult set'
        matches = [level for _, level, message in caplog.record_tuples if message == expected_message]

        assert len(matches) == 1, 'Expected log with message: {}'.format(expected_message)
        assert matches[0] == logging.ERROR

        aggregator.assert_all_metrics_covered()

    def test_no_result(self, caplog, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'gauge'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([[]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()

        with caplog.at_level(logging.DEBUG):
            query_manager.execute()

        expected_message = 'Query test query returned an empty result'
        matches = [level for _, level, message in caplog.record_tuples if message == expected_message]

        assert len(matches) == 1, 'Expected log with message: {}'.format(expected_message)
        assert matches[0] == logging.DEBUG

        aggregator.assert_all_metrics_covered()

    def test_result_length_mismatch(self, caplog, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'gauge'}, {'name': 'test.bar', 'type': 'gauge'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([[1, 2, 3]]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        expected_message = 'Query test query expected 2 columns, got 3'
        matches = [level for _, level, message in caplog.record_tuples if message == expected_message]

        assert len(matches) == 1, 'Expected log with message: {}'.format(expected_message)
        assert matches[0] == logging.ERROR

        aggregator.assert_all_metrics_covered()


class TestTransformers:
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


class TestCustomQueries:
    def test_instance(self, aggregator):
        query_manager = create_query_manager(
            check=AgentCheck(
                'test',
                {},
                [
                    {
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                        ]
                    }
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
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                    ]
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
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                    ]
                },
                [
                    {
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']}
                        ]
                    }
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
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                    ]
                },
                [
                    {
                        'use_global_custom_queries': 'extend',
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']}
                        ],
                    }
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
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                    ]
                },
                [
                    {
                        'use_global_custom_queries': False,
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']}
                        ],
                    }
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
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                    ]
                },
                [
                    {
                        'use_global_custom_queries': 'extend',
                        'custom_queries': [
                            {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                        ],
                    }
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
                        {'query': 'foo', 'columns': [{'name': 'test.foo', 'type': 'gauge'}], 'tags': ['test:bar']}
                    ]
                },
                [
                    {
                        'use_global_custom_queries': 'extend',
                        'custom_queries': [{'columns': [{'name': 'test.bar', 'type': 'gauge'}], 'tags': ['test:bar']}],
                    }
                ],
            ),
            executor=mock_executor([[1]]),
            tags=['test:foo'],
        )

        with pytest.raises(ValueError, match='^field `query` for custom query #1 is required$'):
            query_manager.compile_queries()
