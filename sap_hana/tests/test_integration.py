# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sap_hana import SapHanaCheck

from . import metrics
from .common import connection_flaked

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance, dd_run_check):
    check = SapHanaCheck('sap_hana', {}, [instance])

    attempts = 3
    dd_run_check(check)
    while attempts and connection_flaked(aggregator):
        aggregator.reset()
        dd_run_check(check)
        attempts -= 1

    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'server:{}'.format(instance['server']))
        aggregator.assert_metric_has_tag(metric, 'port:{}'.format(instance['port']))

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance_custom_queries, dd_run_check):
    check = SapHanaCheck('sap_hana', {}, [instance_custom_queries])
    dd_run_check(check)

    for db in ('SYSTEMDB', 'HXE'):
        aggregator.assert_metric(
            'sap_hana.data_volume.total',
            metric_type=0,
            tags=[
                'server:{}'.format(instance_custom_queries['server']),
                'port:{}'.format(instance_custom_queries['port']),
                'db:{}'.format(db),
                'test:sap_hana',
            ],
        )


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'custom_only',
    [
        pytest.param(True, id='Test collect only custom metrics'),
        pytest.param(False, id='Test collect custom and default metrics'),
    ],
)
def test_only_custom_queries(aggregator, dd_run_check, instance_custom_queries, custom_only):
    instance_custom_queries['only_custom_queries'] = custom_only
    check = SapHanaCheck('sap_hana', {}, [instance_custom_queries])
    dd_run_check(check)

    for metric in metrics.STANDARD:
        if custom_only:
            aggregator.assert_metric(metric, count=0)
        else:
            aggregator.assert_metric(metric, at_least=1)

    for _db in ('SYSTEMDB', 'HXE'):
        aggregator.assert_metric('sap_hana.data_volume.total', count=2)

    aggregator.assert_all_metrics_covered()
