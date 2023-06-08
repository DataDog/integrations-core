# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.weaviate import WeaviateCheck
from .common import TEST_METRICS, MOCKED_INSTANCE
from .utils import get_fixture_path


@pytest.mark.unit
def test_check_mock_weaviate(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('weaviate_metrics.txt'))
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in TEST_METRICS:
        aggregator.assert_metric(metric, at_least=1)
    
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('weaviate.openmetrics.health', ServiceCheck.OK)

