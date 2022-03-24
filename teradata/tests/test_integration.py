# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.teradata import TeradataCheck

from .common import CHECK_NAME, EXPECTED_METRICS, SERVICE_CHECK_CONNECT, SERVICE_CHECK_QUERY, TERADATA_SERVER


def test_integration(dd_environment, dd_run_check, datadog_agent, aggregator):
    check = TeradataCheck(CHECK_NAME, {}, [dd_environment])
    dd_run_check(check)
    for m in EXPECTED_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(
        SERVICE_CHECK_CONNECT,
        TeradataCheck.OK,
        tags=["teradata_server:{}".format(TERADATA_SERVER), "teradata_port:1025"],
    )
    aggregator.assert_service_check(
        SERVICE_CHECK_QUERY,
        TeradataCheck.OK,
        tags=["teradata_server:{}".format(TERADATA_SERVER), "teradata_port:1025"],
    )


def test_check(mock_cursor, aggregator, instance, dd_run_check, expected_metrics):
    check = TeradataCheck(CHECK_NAME, {}, [instance])
    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(
            metric['name'],
            metric['value'],
            sorted(metric['tags'] + ['td_env:dev']),
            count=1,
            metric_type=metric['type'],
        )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_service_check(
        SERVICE_CHECK_CONNECT, TeradataCheck.OK, tags=['teradata_server:localhost', 'teradata_port:1025', 'td_env:dev']
    )
    aggregator.assert_service_check(
        SERVICE_CHECK_QUERY, TeradataCheck.OK, tags=['teradata_server:localhost', 'teradata_port:1025', 'td_env:dev']
    )


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, bad_instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = TeradataCheck(CHECK_NAME, {}, [bad_instance])
    with pytest.raises(Exception):
        dd_run_check(check)
        aggregator.assert_service_check(
            SERVICE_CHECK_CONNECT,
            TeradataCheck.CRITICAL,
            tags=["teradata_server:fakeserver.com", "teradata_port:1025"],
        )
        aggregator.assert_service_check(
            SERVICE_CHECK_QUERY, TeradataCheck.CRITICAL, tags=["teradata_server:fakeserver.com", "teradata_port:1025"]
        )
