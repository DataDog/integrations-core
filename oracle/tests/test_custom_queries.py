# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base.utils.db import QueryManager
from datadog_checks.oracle import Oracle

from .common import CHECK_NAME

pytestmark = pytest.mark.unit


def test__check_only_custom_queries(instance):
    """
    Test the default metrics are not called when only_custom queries set to true
    """
    instance['only_custom_queries'] = True

    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._query_manager.queries == []


def test__check_only_custom_queries_not_set(instance):
    """
    Test the default metrics are called when only_custom queries is not set
    """
    instance['only_custom_queries'] = False

    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._query_manager.queries != []


def __test__check_only_custom_queries_set_false(check):
    """
    Test the default metrics are called when only_custom queries is set to False
    """
    assert check._query_manager.queries != []


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


def test_custom_queriess_multiple_results(aggregator, check):
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
