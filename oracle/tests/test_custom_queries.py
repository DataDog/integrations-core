# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base.utils.db import QueryManager
from datadog_checks.oracle import Oracle

from .common import CHECK_NAME

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('only_custom_queries, expected_default_queries', [(True, 0), (False, 3)])
def test_if_only_custom_queries_default_queries_are_not_set(instance, only_custom_queries, expected_default_queries):
    """
    Test the default metrics are not called or not depending on where or not only_custom_queries is set
    """
    instance['only_custom_queries'] = only_custom_queries

    check = Oracle(CHECK_NAME, {}, [instance])

    assert len(check._query_manager.queries) == expected_default_queries


def test_custom_queries(aggregator, check):
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    data = [[["tag_value1", "1"]], [[1, 2, "tag_value2"]]]
    cursor.fetchall.side_effect = lambda: iter(data.pop(0))
    con.cursor.return_value = cursor

    custom_queries = [
        {
            "metric_prefix": "oracle.test1",
            "query": "mocked",
            "columns": [{"name": "tag_name", "type": "tag"}, {"name": "metric", "type": "gauge"}],
            "tags": ["query_tags1"],
        },
        {
            "metric_prefix": "oracle.test2",
            "query": "mocked",
            "columns": [
                {"name": "rate", "type": "rate"},
                {"name": "gauge", "type": "gauge"},
                {"name": "tag_name", "type": "tag"},
            ],
            "tags": ["query_tags2"],
        },
    ]
    check.instance['custom_queries'] = custom_queries
    check._fix_custom_queries()
    check._cached_connection = con
    query_manager = QueryManager(check, check.execute_query_raw, tags=['custom_tag'])
    query_manager.compile_queries()

    query_manager.execute()

    aggregator.assert_metric(
        "oracle.test1.metric", value=1, count=1, tags=["tag_name:tag_value1", "query_tags1", "custom_tag"]
    )
    aggregator.assert_metric(
        "oracle.test2.gauge",
        value=2,
        count=1,
        metric_type=aggregator.GAUGE,
        tags=["tag_name:tag_value2", "query_tags2", "custom_tag"],
    )
    aggregator.assert_metric(
        "oracle.test2.rate",
        value=1,
        count=1,
        metric_type=aggregator.RATE,
        tags=["tag_name:tag_value2", "query_tags2", "custom_tag"],
    )


def test_custom_queries_multiple_results(aggregator, check):
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    data = [["tag_value1", "1"], ["tag_value2", "2"]]
    cursor.fetchall.side_effect = lambda: iter(data)
    con.cursor.return_value = cursor

    custom_queries = [
        {
            "metric_prefix": "oracle.test1",
            "query": "mocked",
            "columns": [{"name": "tag_name", "type": "tag"}, {"name": "metric", "type": "gauge"}],
            "tags": ["query_tags1"],
        }
    ]

    check.instance['custom_queries'] = custom_queries
    check._fix_custom_queries()
    check._cached_connection = con
    query_manager = QueryManager(check, check.execute_query_raw, tags=['custom_tag'])
    query_manager.compile_queries()

    query_manager.execute()

    aggregator.assert_metric(
        "oracle.test1.metric", value=1, count=1, tags=["tag_name:tag_value1", "query_tags1", "custom_tag"]
    )
    aggregator.assert_metric(
        "oracle.test1.metric", value=2, count=1, tags=["tag_name:tag_value2", "query_tags1", "custom_tag"]
    )


def test_custom_queries_metric_prefix_skip_column(aggregator, check, dd_run_check, instance):
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    data = [[["tag_value1", "1"]], [[1, 2, "tag_value2"]]]
    cursor.fetchall.side_effect = lambda: iter(data.pop(0))
    con.cursor.return_value = cursor

    custom_queries = [
        {
            "metric_prefix": "oracle.test1",
            "query": "mocked",
            "columns": [{},  # skip `tag_value1` column
                        {"name": "metric", "type": "gauge"}
                        ],
            "tags": ["query_tags1"],
        },
    ]
    instance['custom_queries'] = custom_queries
    instance['only_custom_queries'] = True
    check = Oracle(CHECK_NAME, {}, [instance])

    with mock.patch("datadog_checks.oracle.oracle.Oracle._connection", new_callable=mock.PropertyMock) as connection:
        connection.return_value = con
        dd_run_check(check)

    aggregator.assert_metric(
        "oracle.test1.metric", value=1, count=1, tags=["query_tags1", "optional:tag1"]
    )
