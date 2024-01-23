# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict, Iterable  # noqa: F401

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.singlestore import SinglestoreCheck


def test_check_default_metrics(mock_cursor, aggregator, instance, expected_default_metrics, dd_run_check):
    # type: (None, AggregatorStub, Dict[str, Any], Iterable, Callable) -> None
    check = SinglestoreCheck('singlestore', {}, [instance])
    dd_run_check(check)
    for metric in expected_default_metrics:
        aggregator.assert_metric(
            metric['name'], metric['value'], metric['tags'] + ["foo:bar"], count=1, metric_type=metric['type']
        )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_service_check(
        'singlestore.can_connect', SinglestoreCheck.OK, tags=['foo:bar', 'singlestore_endpoint:localhost:3306']
    )


def test_check_extended_system_metrics(
    mock_cursor, aggregator, instance, expected_default_metrics, expected_system_metrics, dd_run_check
):
    # type: (None, AggregatorStub, Dict[str, Any], Iterable, Iterable, Callable) -> None
    instance['collect_system_metrics'] = True
    check = SinglestoreCheck('singlestore', {}, [instance])
    dd_run_check(check)
    for metric in expected_default_metrics + expected_system_metrics:
        aggregator.assert_metric(
            metric['name'], metric['value'], metric['tags'] + ["foo:bar"], count=1, metric_type=metric['type']
        )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_service_check(
        'singlestore.can_connect', SinglestoreCheck.OK, tags=['foo:bar', 'singlestore_endpoint:localhost:3306']
    )
