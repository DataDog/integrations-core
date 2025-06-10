# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.falco import FalcoCheck

from .common import METRICS, get_fixture_path


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='\nopenmetrics_endpoint\n  Field required',
    ):
        check = FalcoCheck('falco', {}, [{}])
        dd_run_check(check)


def test_check_falco(dd_run_check, aggregator, instance):
    mock_responses = [
        MockResponse(file_path=get_fixture_path("falco_metrics.txt")),
    ]

    with mock.patch('requests.get', side_effect=mock_responses):
        dd_run_check(FalcoCheck('falco', {}, [instance]))

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("falco.openmetrics.health", ServiceCheck.OK)
