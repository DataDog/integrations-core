# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.supabase import SupabaseCheck

from .common import (
    PRIVILEGED_METRICS,
    PRIVILEGED_METRICS_INSTANCE,
    PRIVILEGED_METRICS_NAMESPACE,
    STORAGE_API_INSTANCE,
    STORAGE_API_METRICS,
    STORAGE_API_METRICS_NAMESPACE,
    get_fixture_path,
)


@pytest.mark.parametrize(
    'namespace, instance, metrics, fixture_name,',
    [
        (PRIVILEGED_METRICS_NAMESPACE, PRIVILEGED_METRICS_INSTANCE, PRIVILEGED_METRICS, 'privileged_metrics.txt'),
        (STORAGE_API_METRICS_NAMESPACE, STORAGE_API_INSTANCE, STORAGE_API_METRICS, 'storage_api_metrics.txt'),
    ],
)
def test_check_mock_supabase_openmetrics(
    dd_run_check, instance, aggregator, fixture_name, metrics, fake_http, fake_http_response, namespace
):
    endpoint = instance.get('privileged_metrics_endpoint') or instance['storage_api_endpoint']
    fake_http_response(endpoint, Path(get_fixture_path(fixture_name)).read_bytes())
    check = SupabaseCheck('supabase', {}, [instance])
    dd_run_check(check)

    for metric in metrics:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    fake_http.assert_all_responses_consumed()
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(f'{namespace}.openmetrics.health', ServiceCheck.OK)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='Must specify at least one of the following:`privileged_metrics_endpoint` or `storage_api_endpoint`.',
    ):
        check = SupabaseCheck('supabase', {}, [{}])
        dd_run_check(check)
