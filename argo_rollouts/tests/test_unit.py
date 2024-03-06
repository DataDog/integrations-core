# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.argo_rollouts import ArgoRolloutsCheck
from datadog_checks.base.constants import ServiceCheck

# from datadog_checks.dev.utils import get_metadata_metrics
from .common import OM_METRICS, OM_MOCKED_INSTANCE, get_fixture_path

pytestmark = pytest.mark.unit


def test_check_mock_argo_rollouts_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('openmetrics.txt'))
    check = ArgoRolloutsCheck('argo_rollouts', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in OM_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    # aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('argo_rollouts.openmetrics.health', ServiceCheck.OK)


def test_check_mock_invalid_argo_rollouts_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = ArgoRolloutsCheck('argo_rollouts', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('argo_rollouts.openmetrics.health', ServiceCheck.CRITICAL)
