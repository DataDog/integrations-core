# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db import QueryManager

from .common import create_query_manager, mock_executor


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

    def test_custom_query_not_string(self):
        query_manager = create_query_manager({'name': 'custom query #1', 'query': {'query': 'example'}})

        with pytest.raises(ValueError, match='^field `query` for custom query #1 must be a string$'):
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
            {'name': 'test query', 'query': 'foo', 'columns': [{}, {'foo': 'bar'}], 'tags': ['test:bar']},
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
            {'name': 'test query', 'query': 'foo', 'columns': [{'name': 'test.foo'}], 'tags': ['test:bar']},
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

    def test_column_duplicate_error(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}, {'name': 'test.foo', 'type': 'source'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^the name test.foo of test query was already defined in column #1$'):
            query_manager.compile_queries()

    def test_compilation_idempotent(self):
        query_manager = create_query_manager(
            {'name': 'test query', 'query': 'foo', 'columns': [{}], 'tags': ['test:bar']}
        )

        query_manager.compile_queries()
        query_manager.compile_queries()

    def test_extras_not_list(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': 'bar',
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^field `extras` for test query must be a list$'):
            query_manager.compile_queries()

    def test_extra_not_dict(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [['extras']],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^extra #1 of test query is not a mapping$'):
            query_manager.compile_queries()

    def test_extra_no_name(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^field `name` for extra #1 of test query is required$'):
            query_manager.compile_queries()

    def test_extra_name_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 5}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^field `name` for extra #1 of test query must be a string$'):
            query_manager.compile_queries()

    def test_extra_no_type(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^field `type` for extra foo of test query is required$'):
            query_manager.compile_queries()

    def test_extra_type_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 5}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^field `type` for extra foo of test query must be a string$'):
            query_manager.compile_queries()

    def test_extra_type_unknown(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'something'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^unknown type `something` for extra foo of test query$'):
            query_manager.compile_queries()

    def test_extra_type_submission_no_source(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'gauge'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^field `source` for extra foo of test query is required$'):
            query_manager.compile_queries()

    def test_extra_duplicate_error(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [
                    {'name': 'foo', 'type': 'gauge', 'source': 'test.foo'},
                    {'name': 'foo', 'type': 'count', 'source': 'test.foo'},
                ],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^the name foo of test query was already defined in extra #1$'):
            query_manager.compile_queries()

    def test_column_extra_duplicate_error(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'test.foo', 'type': 'gauge', 'source': 'test.foo'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(ValueError, match='^the name test.foo of test query was already defined in column #1$'):
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

    def test_expression_none(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'expression'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `expression` for extra foo of test query: '
                'the `expression` parameter is required$'
            ),
        ):
            query_manager.compile_queries()

    def test_expression_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'expression', 'expression': 5}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `expression` for extra foo of test query: '
                'the `expression` parameter must be a string$'
            ),
        ):
            query_manager.compile_queries()

    def test_expression_empty(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'expression', 'expression': ''}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `expression` for extra foo of test query: '
                'the `expression` parameter must not be empty$'
            ),
        ):
            query_manager.compile_queries()

    def test_expression_submit_type_unknown(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'expression', 'expression': '5', 'submit_type': 'something'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match='^error compiling type `expression` for extra foo of test query: unknown submit_type `something`$',
        ):
            query_manager.compile_queries()

    @pytest.mark.parametrize('expression', ['import os', 'raise Exception', 'foo = 5'])
    def test_expression_compile_error(self, expression):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'expression', 'expression': expression}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            SyntaxError, match='^error compiling type `expression` for extra foo of test query: invalid syntax'
        ):
            query_manager.compile_queries()

    def test_percent_no_part(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'percent'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match='^error compiling type `percent` for extra foo of test query: the `part` parameter is required$',
        ):
            query_manager.compile_queries()

    def test_percent_part_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'percent', 'part': 5}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match='^error compiling type `percent` for extra foo of test query: the `part` parameter must be a string$',
        ):
            query_manager.compile_queries()

    def test_percent_part_not_source(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'pct', 'type': 'percent', 'part': 'foo'}, {'name': 'foo', 'expression': '5'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `percent` for extra pct of test query: '
                'the `part` parameter `foo` is not an available source$'
            ),
        ):
            query_manager.compile_queries()

    def test_percent_no_total(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'percent', 'part': 'test.foo'}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match='^error compiling type `percent` for extra foo of test query: the `total` parameter is required$',
        ):
            query_manager.compile_queries()

    def test_percent_total_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [{'name': 'foo', 'type': 'percent', 'part': 'test.foo', 'total': 5}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `percent` for extra foo of test query: '
                'the `total` parameter must be a string$'
            ),
        ):
            query_manager.compile_queries()

    def test_percent_total_not_source(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'source'}],
                'extras': [
                    {'name': 'pct', 'type': 'percent', 'part': 'test.foo', 'total': 'foo'},
                    {'name': 'foo', 'expression': '5'},
                ],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `percent` for extra pct of test query: '
                'the `total` parameter `foo` is not an available source$'
            ),
        ):
            query_manager.compile_queries()

    def test_service_check_no_status_map(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'service_check'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['known']]),
            tags=['test:foo'],
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `service_check` for column test.foo of test query: '
                'the `status_map` parameter is required$'
            ),
        ):
            query_manager.compile_queries()

    def test_service_check_status_map_not_dict(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'service_check', 'status_map': 5}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['known']]),
            tags=['test:foo'],
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `service_check` for column test.foo of test query: '
                'the `status_map` parameter must be a mapping$'
            ),
        ):
            query_manager.compile_queries()

    def test_service_check_status_map_empty(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'service_check', 'status_map': {}}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['known']]),
            tags=['test:foo'],
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `service_check` for column test.foo of test query: '
                'the `status_map` parameter must not be empty$'
            ),
        ):
            query_manager.compile_queries()

    def test_service_check_status_map_status_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'service_check', 'status_map': {'known': 0}}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['known']]),
            tags=['test:foo'],
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `service_check` for column test.foo of test query: '
                'status `0` for value `known` of parameter `status_map` is not a string$'
            ),
        ):
            query_manager.compile_queries()

    def test_service_check_status_map_status_invalid(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'service_check', 'status_map': {'known': '0k'}}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['known']]),
            tags=['test:foo'],
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `service_check` for column test.foo of test query: '
                'invalid status `0k` for value `known` of parameter `status_map`$'
            ),
        ):
            query_manager.compile_queries()

    def test_time_elapsed_format_not_string(self):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'time_elapsed', 'format': 5}],
                'tags': ['test:bar'],
            }
        )

        with pytest.raises(
            ValueError,
            match=(
                '^error compiling type `time_elapsed` for column test.foo of test query: '
                'the `format` parameter must be a string$'
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

    def test_runtime_tags(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test.foo', 'type': 'count'}, {'name': 'tag', 'type': 'tag'}],
            },
            executor=mock_executor([[3, 'tag1'], [7, 'tag2'], [5, 'tag1']]),
            tags=['test:init'],
        )
        query_manager.compile_queries()
        query_manager.execute(extra_tags=['test:runtime'])

        aggregator.assert_metric(
            'test.foo', 8, metric_type=aggregator.COUNT, tags=['test:init', 'test:runtime', 'tag:tag1']
        )
        aggregator.assert_metric(
            'test.foo', 7, metric_type=aggregator.COUNT, tags=['test:init', 'test:runtime', 'tag:tag2']
        )
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
                    {'name': 'test.baz', 'type': 'gauge', 'raw': True},
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
        aggregator.assert_metric('test.baz', 2, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar'])
        aggregator.assert_all_metrics_covered()

    def test_queries_are_copied(self):
        class MyCheck(AgentCheck):
            pass

        check1 = MyCheck('test', {}, [{}])
        check2 = MyCheck('test', {}, [{}])
        dummy_query = {
            'name': 'test query',
            'query': 'foo',
            'columns': [
                {'name': 'test.foo', 'type': 'gauge', 'tags': ['override:ok']},
                {'name': 'test.baz', 'type': 'gauge', 'raw': True},
            ],
            'tags': ['test:bar'],
        }
        query_manager1 = QueryManager(check1, mock_executor(), [dummy_query])
        query_manager2 = QueryManager(check2, mock_executor(), [dummy_query])
        query_manager1.compile_queries()
        query_manager2.compile_queries()
        assert not id(query_manager1.queries[0]) == id(
            query_manager2.queries[0]
        ), "QueryManager does not copy the queries"

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

    def test_extra_transformer_error(self, caplog, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'test', 'type': 'tag'}, {'name': 'test.foo', 'type': 'gauge'}],
                'extras': [
                    {'name': 'nope', 'expression': 'test.foo / 0', 'submit_type': 'gauge'},
                    {'name': 'foo', 'expression': 'test.foo / 2', 'submit_type': 'gauge'},
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
        aggregator.assert_metric('foo', 2.5, metric_type=aggregator.GAUGE, tags=['test:foo', 'test:bar', 'test:tag1'])

        expected_message = 'Error transforming nope'
        matches = [level for _, level, message in caplog.record_tuples if message.startswith(expected_message)]

        assert len(matches) == 1, 'Expected log starting with message: {}'.format(expected_message)
        assert matches[0] == logging.ERROR

        aggregator.assert_all_metrics_covered()

    def test_metadata(self, aggregator, datadog_agent):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [{'name': 'version', 'type': 'metadata'}],
                'tags': ['test:bar'],
            },
            executor=mock_executor([['1.2.3-rc.4+5']]),
            tags=['test:foo'],
        )
        query_manager.compile_queries()
        query_manager.execute()

        version_metadata = {
            'version.major': '1',
            'version.minor': '2',
            'version.patch': '3',
            'version.release': 'rc.4',
            'version.build': '5',
            'version.raw': '1.2.3-rc.4+5',
            'version.scheme': 'semver',
        }

        datadog_agent.assert_metadata('test:instance', version_metadata)
        datadog_agent.assert_metadata_count(len(version_metadata))
        aggregator.assert_all_metrics_covered()

    def test_hostname(self, aggregator):
        query_manager = create_query_manager(
            {
                'name': 'test query',
                'query': 'foo',
                'columns': [
                    {'name': 'test.foo', 'type': 'count'},
                    {'name': 'tag', 'type': 'tag'},
                    {"name": "_source", "type": "source"},
                ],
                'tags': ['test:bar'],
                "extras": [{"name": "test.baz", "expression": "_source * 1000", 'submit_type': 'gauge'}],
            },
            executor=mock_executor([[3, 'tag1', 2], [7, 'tag2', 5], [5, 'tag1', 6]]),
            tags=['test:foo'],
            hostname="test-hostname",
        )
        query_manager.compile_queries()
        query_manager.execute()

        aggregator.assert_metric(
            'test.foo',
            8,
            metric_type=aggregator.COUNT,
            tags=['test:foo', 'test:bar', 'tag:tag1'],
            hostname="test-hostname",
        )
        aggregator.assert_metric(
            'test.foo',
            7,
            metric_type=aggregator.COUNT,
            tags=['test:foo', 'test:bar', 'tag:tag2'],
            hostname="test-hostname",
        )

        for val, tag in [(2000, 'tag1'), (5000, 'tag2'), (6000, 'tag1')]:
            aggregator.assert_metric(
                'test.baz',
                val,
                metric_type=aggregator.GAUGE,
                tags=['test:foo', 'test:bar', 'tag:{}'.format(tag)],
                hostname="test-hostname",
            )

        aggregator.assert_all_metrics_covered()
