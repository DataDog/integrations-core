# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import create_query_manager, mock_executor


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
