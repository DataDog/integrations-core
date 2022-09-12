# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

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
    _assert_standard_metrics(aggregator, instance)
    aggregator.assert_all_metrics_covered()


def test_check_invalid_schema(aggregator, instance, dd_run_check):
    instance["schema"] = "UNKNOWN_SCHEMA"
    check = SapHanaCheck('sap_hana', {}, [instance])
    _run_until_stable(dd_run_check, check, aggregator, mock_log=True)

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

    for call_args in check.log.error.call_args_list:
        assert "invalid schema name: UNKNOWN_SCHEMA" in call_args[0][2]

    assert check.log.error.call_count == 9


def _run_until_stable(dd_run_check, check, aggregator, mock_log=False):
    retries = 3
    if mock_log:
        check.log = mock.MagicMock()
    dd_run_check(check)
    while retries and connection_flaked(aggregator):
        if mock_log:
            check.log.reset_mock()
        dd_run_check(check)
        time.sleep(4 - retries)
        retries -= 1


def _assert_standard_metrics(aggregator, instance):
    # Not all metrics are present in every check run
    missing_metrics = []
    for metric in metrics.STANDARD:
        if metric in aggregator.metric_names:
            aggregator.assert_metric_has_tag(metric, 'server:{}'.format(instance['server']))
            aggregator.assert_metric_has_tag(metric, 'port:{}'.format(instance['port']))
        else:
            missing_metrics.append(metric)
    assert len(missing_metrics) / len(metrics.STANDARD) < 0.1, 'Missing metrics: %s\nPresent metrics: %s' % (
        missing_metrics,
        aggregator.metric_names,
    )


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

    if custom_only:
        for metric in metrics.STANDARD:
            aggregator.assert_metric(metric, count=0)
    else:
        _assert_standard_metrics(aggregator, instance_custom_queries)

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
