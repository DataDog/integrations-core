# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import mock
import pytest
from requests.exceptions import HTTPError

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.marklogic import MarklogicCheck

from .common import INSTANCE, INSTANCE_FILTERS
from .metrics import GLOBAL_METRICS, RESOURCE_STORAGE_FOREST_METRICS, STORAGE_FOREST_METRICS, STORAGE_HOST_METRICS


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator):
    # type: (AggregatorStub) -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE])

    check.check(INSTANCE)

    tags = ['foo:bar']

    for metric in GLOBAL_METRICS:
        aggregator.assert_metric(metric, tags=tags)

    storage_tag_prefixes = ['storage_path', 'host_name', 'host_id']
    for metric in STORAGE_HOST_METRICS:
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
        for prefix in storage_tag_prefixes:
            aggregator.assert_metric_has_tag_prefix(metric, prefix)
    for metric in STORAGE_FOREST_METRICS:
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
        for prefix in storage_tag_prefixes + ['forest_id', 'forest_name']:
            aggregator.assert_metric_has_tag_prefix(metric, prefix)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check_with_filters(aggregator):
    # type: (AggregatorStub) -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE_FILTERS])

    check.check(INSTANCE_FILTERS)

    # Not resource filters-related
    for metric in GLOBAL_METRICS:
        aggregator.assert_metric(metric, at_least=1)  # TODO: remove duplication with filters
    for metric in STORAGE_HOST_METRICS:
        aggregator.assert_metric(metric, count=2)
    for metric in STORAGE_FOREST_METRICS:
        aggregator.assert_metric(metric, at_least=10)  # TODO: remove duplication with filters

    # Metrics from resource filters
    for metric in RESOURCE_STORAGE_FOREST_METRICS:
        aggregator.assert_metric(metric, tags=['forest_name:Security'], count=1)
    for metric in [
        'marklogic.requests.query-count',
        'marklogic.requests.total-requests',
        'marklogic.requests.update-count',
    ]:
        aggregator.assert_metric(metric, tags=['server_name:Admin', 'group_name:Default'], count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    # type: (Any) -> None
    aggregator = dd_agent_check(INSTANCE, rate=True)

    for metric in GLOBAL_METRICS:
        aggregator.assert_metric(metric)
    for metric in STORAGE_HOST_METRICS:
        aggregator.assert_metric(metric, count=2)  # TODO: remove duplication with filters
    for metric in STORAGE_FOREST_METRICS:
        aggregator.assert_metric(metric, count=20)  # TODO: remove duplication with filters

    aggregator.assert_all_metrics_covered()


def test_submit_service_checks(aggregator, caplog):
    # type: (AggregatorStub, Any) -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE])

    health_mocked_data = {
        'cluster-health-report': [
            {
                'resource-type': 'database',
                'resource-name': 'Last-Login',
                'code': 'HEALTH-DATABASE-NO-BACKUP',
                'message': 'Database has never been backed up.',
            },
            {'resource-type': 'database', 'resource-name': 'Fab', 'code': 'UNKNOWN'},
        ]
    }

    with mock.patch('datadog_checks.marklogic.api.MarkLogicApi.get_health', return_value=health_mocked_data):
        check.submit_service_checks()

        aggregator.assert_service_check(
            'marklogic.resource.health',
            MarklogicCheck.OK,
            tags=['foo:bar', 'resource:Last-Login'],
            message='HEALTH-DATABASE-NO-BACKUP: Database has never been backed up.',
            count=1,
        )
        aggregator.assert_service_check(
            'marklogic.resource.health',
            MarklogicCheck.UNKNOWN,
            tags=['foo:bar', 'resource:Fab'],
            message='UNKNOWN: No message.',
            count=1,
        )
        aggregator.assert_service_check('marklogic.can_connect', MarklogicCheck.OK, count=1)

    aggregator.reset()
    caplog.clear()

    with mock.patch('datadog_checks.marklogic.api.MarkLogicApi.get_health', side_effect=HTTPError):
        check.submit_service_checks()

        aggregator.assert_service_check('marklogic.can_connect', MarklogicCheck.CRITICAL, count=1)

    aggregator.reset()
    caplog.clear()

    with mock.patch('datadog_checks.marklogic.api.MarkLogicApi.get_health', side_effect=Exception("exception")):
        check.submit_service_checks()

        assert "Failed to parse the resources health" in caplog.text
        # Exception log
        assert "Exception: exception" in caplog.text
