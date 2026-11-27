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
    'namespace, instance, metrics, fixture_name, endpoint_option',
    [
        (
            PRIVILEGED_METRICS_NAMESPACE,
            PRIVILEGED_METRICS_INSTANCE,
            PRIVILEGED_METRICS,
            'privileged_metrics.txt',
            'privileged_metrics_endpoint',
        ),
        (
            STORAGE_API_METRICS_NAMESPACE,
            STORAGE_API_INSTANCE,
            STORAGE_API_METRICS,
            'storage_api_metrics.txt',
            'storage_api_endpoint',
        ),
    ],
)
def test_check_mock_supabase_openmetrics(
    dd_run_check, instance, aggregator, fixture_name, endpoint_option, metrics, fake_http_response, namespace
):
    fake_http_response(instance[endpoint_option], Path(get_fixture_path(fixture_name)).read_bytes())
    check = SupabaseCheck('supabase', {}, [instance])
    dd_run_check(check)

    for metric in metrics:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

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
