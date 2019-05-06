# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.vertica import VerticaCheck

from .metrics import ALL_METRICS


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    check = VerticaCheck('vertica', {}, [instance])
    check.check(instance)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


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
