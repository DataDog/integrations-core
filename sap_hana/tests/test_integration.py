# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from mock.mock import ANY, call

from datadog_checks.sap_hana import SapHanaCheck

from . import metrics
from .common import CAN_CONNECT_SERVICE_CHECK, connection_flaked

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, instance, dd_run_check):
    check = SapHanaCheck('sap_hana', {}, [instance])
    _run_until_stable(dd_run_check, check, aggregator)

    aggregator.assert_service_check(CAN_CONNECT_SERVICE_CHECK, SapHanaCheck.OK)
    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'server:{}'.format(instance['server']))
        aggregator.assert_metric_has_tag(metric, 'port:{}'.format(instance['port']))

    aggregator.assert_all_metrics_covered()


def test_check_invalid_schema(aggregator, instance, dd_run_check):
    instance["schema"] = "UNKNOWN_SCHEMA"
    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()
    dd_run_check(check)

    check.log.error.assert_has_calls(
        calls=[
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_BACKUP_PROGRESS', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_LICENSES', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_CONNECTIONS', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_DISK_USAGE', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_SERVICE_MEMORY', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_SERVICE_COMPONENT_MEMORY', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_RS_MEMORY', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_SERVICE_STATISTICS', ANY),
            call('Error querying %s: %s', 'UNKNOWN_SCHEMA.M_VOLUME_IO_TOTAL_STATISTICS', ANY),
        ],
        any_order=False,
    )

    assert check.log.error.call_count == 9

    for call_args in check.log.error.call_args_list:
        assert "invalid schema name: UNKNOWN_SCHEMA" in call_args[0][2]


def _run_until_stable(dd_run_check, check, aggregator):
    retries = 3
    dd_run_check(check)
    while retries and connection_flaked(aggregator):
        aggregator.reset()
        dd_run_check(check)
        retries -= 1


@pytest.mark.parametrize(
    'custom_only',
    [
        pytest.param(True, id='Test collect only custom metrics'),
        pytest.param(False, id='Test collect custom and default metrics'),
    ],
)
def test_custom_queries(aggregator, dd_run_check, instance_custom_queries, custom_only):
    instance_custom_queries['only_custom_queries'] = custom_only
    check = SapHanaCheck('sap_hana', {}, [instance_custom_queries])
    _run_until_stable(dd_run_check, check, aggregator)

    for metric in metrics.STANDARD:
        if custom_only:
            aggregator.assert_metric(metric, count=0)
        else:
            # Some metrics are emitted twice, once per database
            aggregator.assert_metric(metric, at_least=1)

    for _db in ('SYSTEMDB', 'HXE'):
        aggregator.assert_metric(
            'sap_hana.data_volume.total',
            metric_type=0,
            tags=[
                'server:{}'.format(instance_custom_queries['server']),
                'port:{}'.format(instance_custom_queries['port']),
                'db:{}'.format(_db),
                'test:sap_hana',
            ],
        )

    aggregator.assert_all_metrics_covered()
