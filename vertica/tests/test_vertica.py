# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev import TempDir
from datadog_checks.vertica import VerticaCheck

from .metrics import ALL_METRICS


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in ALL_METRICS:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    check = VerticaCheck('vertica', {}, [instance])
    check.check(instance)

    for metric in ALL_METRICS:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_check_client_log(aggregator, instance):
    with TempDir() as temp_dir:
        log_file = os.path.join(temp_dir, 'vertica_client_lib.log')
        instance['client_lib_log_level'] = 'DEBUG'
        instance['client_lib_log_path'] = log_file

        check = VerticaCheck('vertica', {}, [instance])
        check.check(instance)

        with open(log_file) as f:
            assert "Establishing connection to host" in f.read()


@pytest.mark.usefixtures('dd_environment')
def test_check_connection_load_balance(instance):
    instance['connection_load_balance'] = True
    check = VerticaCheck('vertica', {}, [instance])

    def mock_reset_connection():
        raise Exception('reset_connection was called')

    with mock.patch('vertica_python.vertica.connection.Connection.reset_connection', side_effect=mock_reset_connection):
        check.check(instance)

        with pytest.raises(Exception, match='reset_connection was called'):
            check.check(instance)


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance):
    instance['custom_queries'] = [
        {
            'tags': ['test:vertica'],
            'query': 'SELECT force_outer, table_name FROM v_catalog.tables',
            'columns': [{'name': 'table.force_outer', 'type': 'gauge'}, {'name': 'table_name', 'type': 'tag'}],
        }
    ]

    check = VerticaCheck('vertica', {}, [instance])
    check.check(instance)

    aggregator.assert_metric(
        'vertica.table.force_outer', metric_type=0, tags=['db:datadog', 'foo:bar', 'test:vertica', 'table_name:datadog']
    )
