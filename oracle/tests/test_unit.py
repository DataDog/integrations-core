# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest

from datadog_checks.base.utils.db import Query
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.oracle import Oracle, queries

from .common import CHECK_NAME

pytestmark = pytest.mark.unit


def test_bad_connection_emits_critical_service_check(aggregator, dd_run_check, bad_instance):
    """
    Test the right service check is sent upon _get_connection failures
    """
    bad_instance.update({'tags': ['optional:tag1']})
    oracle_check = Oracle(CHECK_NAME, {}, [bad_instance])
    expected_tags = ['server:localhost:1521', 'optional:tag1']

    dd_run_check(oracle_check)
    aggregator.assert_service_check("oracle.can_connect", Oracle.CRITICAL, count=1, tags=expected_tags)
    aggregator.assert_service_check("oracle.can_query", Oracle.CRITICAL, count=1, tags=expected_tags)
    assert oracle_check._cached_connection is None


def test_sys_metrics(aggregator, check):
    con = mock.MagicMock()
    cur = mock.MagicMock()
    con.cursor.return_value = cur
    metrics = copy.deepcopy(queries.SystemMetrics['columns'][1]['items'])
    cur.fetchall.return_value = zip([0] * len(metrics.keys()), metrics.keys(), strict=True)

    check._cached_connection = con
    check._query_manager.queries = [Query(queries.SystemMetrics)]
    check._query_manager.tags = ['custom_tag']
    check._query_manager.compile_queries()
    check._query_manager.execute()

    for metric in metrics.values():
        aggregator.assert_metric('oracle.{}'.format(metric['name']), count=1, value=0, tags=['custom_tag'])
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_process_metrics(aggregator, check):
    con = mock.MagicMock()
    cur = mock.MagicMock()
    con.cursor.return_value = cur
    metrics = copy.deepcopy(queries.ProcessMetrics['columns'][2:])
    programs = [
        "PSEUDO",
        "oracle@localhost.localdomain (PMON)",
        "oracle@localhost.localdomain (PSP0)",
        "oracle@localhost.localdomain (VKTM)",
    ]
    cur.fetchall.return_value = [[i, program] + ([0] * len(metrics)) for (i, program) in enumerate(programs)]

    check._cached_connection = con
    check._query_manager.queries = [Query(queries.ProcessMetrics)]
    check._query_manager.tags = ['custom_tag']
    check._query_manager.compile_queries()
    check._query_manager.execute()

    for i, metric in enumerate(metrics):
        expected_program = programs[i]
        aggregator.assert_metric(
            'oracle.{}'.format(metric['name']),
            count=1,
            value=0,
            tags=['custom_tag', 'pid:{}'.format(i), 'program:{}'.format(expected_program)],
        )


def test_tablespace_metrics(aggregator, check):
    con = mock.MagicMock()
    cur = mock.MagicMock()
    cur.fetchall.return_value = [
        ["offline", 0, 100, 0, 1],
        ["normal", 50, 100, 50, 0],
        ["full", 100, 100, 100, 0],
        ["size_0", 1, 0, 100, 0],
    ]
    con.cursor.return_value = cur

    check._cached_connection = con
    check._query_manager.queries = [Query(queries.TableSpaceMetrics)]
    check._query_manager.tags = ['custom_tag']
    check._query_manager.compile_queries()
    check._query_manager.execute()

    # Offline tablespace
    tags = ["custom_tag", "tablespace:offline"]
    aggregator.assert_metric("oracle.tablespace.used", value=0, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=0, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=1, count=1, tags=tags)

    # Normal tablespace
    tags = ["custom_tag", "tablespace:normal"]
    aggregator.assert_metric("oracle.tablespace.used", value=50, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=50, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=0, count=1, tags=tags)

    # Full tablespace
    tags = ["custom_tag", "tablespace:full"]
    aggregator.assert_metric("oracle.tablespace.used", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=0, count=1, tags=tags)

    # Size 0 tablespace
    tags = ["custom_tag", "tablespace:size_0"]
    aggregator.assert_metric("oracle.tablespace.used", value=1, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.size", value=0, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.in_use", value=100, count=1, tags=tags)
    aggregator.assert_metric("oracle.tablespace.offline", value=0, count=1, tags=tags)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_handle_query_error_when_not_connected_does_no_fail(instance):
    oracle_check = Oracle(CHECK_NAME, {}, [instance])

    error = oracle_check.handle_query_error('foo')
    assert error == 'foo'


def test_handle_query_error_when_connected_disconnects_and_resets_connection(instance):
    oracle_check = Oracle(CHECK_NAME, {}, [instance])
    cached_connection = mock.Mock()
    oracle_check._cached_connection = cached_connection

    error = oracle_check.handle_query_error('foo')
    assert error == 'foo'
    assert oracle_check._cached_connection is None
    cached_connection.assert_has_calls([mock.call.close()])
