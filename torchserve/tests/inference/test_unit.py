# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from ..conftest import read_fixture

pytestmark = pytest.mark.unit


def test_check(dd_run_check, aggregator, check, mocked_inference_instance, fake_http_response):
    fake_http_response('http://torchserve:8080/ping', read_fixture('inference/healthy.json'))
    dd_run_check(check(mocked_inference_instance))

    aggregator.assert_service_check(
        "torchserve.inference_api.health",
        AgentCheck.OK,
        tags=[f"inference_api_url:{mocked_inference_instance['inference_api_url']}"],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_check_unhealthy(dd_run_check, aggregator, check, mocked_inference_instance, fake_http_response):
    fake_http_response('http://torchserve:8080/ping', read_fixture('inference/unhealthy.json'), status_code=500)

    with pytest.raises(Exception, match="500 Server Error"):
        dd_run_check(check(mocked_inference_instance))

    aggregator.assert_service_check(
        "torchserve.inference_api.health",
        AgentCheck.CRITICAL,
        tags=[f"inference_api_url:{mocked_inference_instance['inference_api_url']}"],
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
