# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.vertica import VerticaCheck

from . import common
from .metrics import ALL_METRICS


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in ALL_METRICS:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, datadog_agent, instance):
    check = VerticaCheck('vertica', {}, [instance])
    check.check_id = 'test:123'
    check.check(instance)

    for metric in ALL_METRICS:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_all_metrics_covered()

    version_metadata = {'version.scheme': 'semver', 'version.major': os.environ['VERTICA_VERSION'][0]}
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata) + 4)


@pytest.mark.usefixtures('dd_environment')
def test_vertica_log_file_not_created(aggregator, instance):
    instance['client_lib_log_level'] = 'DEBUG'

    vertica_default_log = os.path.join(os.path.dirname(common.HERE), 'vertica_python.log')
    if os.path.exists(vertica_default_log):
        os.remove(vertica_default_log)

    check = VerticaCheck('vertica', {}, [instance])
    check.check(instance)

    assert not os.path.exists(vertica_default_log)


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
