# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

# from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.litellm import LitellmCheck

from .common import (
    METRICS,
    OM_MOCKED_INSTANCE,
    get_fixture_path,
)


def test_kyverno_mock_metrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.OK)


def test_kyverno_mock_invalid_endpoint(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = LitellmCheck('litellm', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('litellm.openmetrics.health', ServiceCheck.CRITICAL)
