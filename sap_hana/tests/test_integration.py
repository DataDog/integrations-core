# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sap_hana import SapHanaCheck

from . import metrics

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_sap_hana(aggregator, instance):
    check = SapHanaCheck('sap_hana', {}, [instance])
    check.check(instance)

    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'server:{}'.format(instance['server']))
        aggregator.assert_metric_has_tag(metric, 'port:{}'.format(instance['port']))

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance):
    instance['custom_queries'] = [
        {
            'tags': ['test:sap_hana'],
            'query': 'SELECT DATABASE_NAME, COUNT(*) FROM SYS_DATABASES.M_DATA_VOLUMES GROUP BY DATABASE_NAME',
            'columns': [{'name': 'db', 'type': 'tag'}, {'name': 'data_volume.total', 'type': 'gauge'}],
        }
    ]

    check = SapHanaCheck('sap_hana', {}, [instance])
    check.check(instance)

    for db in ('SYSTEMDB', 'HXE'):
        aggregator.assert_metric(
            'sap_hana.data_volume.total',
            metric_type=0,
            tags=[
                'server:{}'.format(instance['server']),
                'port:{}'.format(instance['port']),
                'db:{}'.format(db),
                'test:sap_hana',
            ],
        )
