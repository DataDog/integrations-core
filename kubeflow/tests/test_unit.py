# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubeflow import KubeflowCheck

from .common import METRICS_MOCK, get_fixture_path


def test_check_kubeflow(dd_run_check, aggregator, instance, fake_http, fake_http_response):
    fake_http_response(instance['openmetrics_endpoint'], Path(get_fixture_path('kubeflow_metrics.txt')).read_bytes())
    check = KubeflowCheck('kubeflow', {}, [instance])
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    fake_http.assert_all_responses_consumed()
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('kubeflow.openmetrics.health', ServiceCheck.OK)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = KubeflowCheck('KubeflowCheck', {}, [{}])
        dd_run_check(check)
