# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_check(dd_run_check, aggregator, check, inference_instance):
    dd_run_check(check(inference_instance))

    aggregator.assert_service_check(
        "torchserve.inference_api.health",
        AgentCheck.OK,
        tags=[f"inference_api_url:{inference_instance['inference_api_url']}"],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_unknown_url(dd_run_check, aggregator, check, inference_instance):

    inference_instance["inference_api_url"] = "http://unknown_host:12345"
    inference_instance["timeout"] = 1  # speedup the test

    with pytest.raises(Exception, match="Max retries exceeded with url: /ping"):
        dd_run_check(check(inference_instance))

    aggregator.assert_service_check(
        "torchserve.inference_api.health",
        AgentCheck.CRITICAL,
        tags=[f"inference_api_url:{inference_instance['inference_api_url']}"],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
