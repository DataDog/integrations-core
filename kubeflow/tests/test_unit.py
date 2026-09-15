# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kubeflow import KubeflowCheck
from datadog_checks.kubeflow.metrics import METRIC_MAP, RENAME_LABELS_MAP

from .common import METRICS_MOCK, get_fixture_path

pytestmark = pytest.mark.unit


def test_check_kubeflow(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('kubeflow_metrics.txt'))
    check = KubeflowCheck('kubeflow', {}, [instance])
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

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


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:11 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KubeflowCheck.DEFAULT_METRIC_LIMIT == 0


def test_get_default_config_uses_metric_map_and_rename_labels(instance):
    # Confirms get_default_config wires METRIC_MAP/RENAME_LABELS_MAP into the returned config.
    check = KubeflowCheck('kubeflow', {}, [instance])
    config = check.get_default_config()
    assert config['metrics'] == [METRIC_MAP]
    assert config['rename_labels'] == RENAME_LABELS_MAP
