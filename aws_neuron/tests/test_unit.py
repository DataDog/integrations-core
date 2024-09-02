# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.aws_neuron import AwsNeuronCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import RENAMED_LABELS, TEST_METRICS, get_fixture_path


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('aws_neuron_metrics.txt'))

    check = AwsNeuronCheck('aws_neuron', {}, [instance])
    dd_run_check(check)

    for metric, metric_type in TEST_METRICS.items():
        aggregator.assert_metric(metric, metric_type=aggregator.METRIC_ENUM_MAP[metric_type])
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    for metric, tag in RENAMED_LABELS.items():
        aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = AwsNeuronCheck('aws_neuron', {}, [{}])
        dd_run_check(check)


def test_custom_validation(dd_run_check):
    endpoint = 'aws_neuron:2112/metrics'
    with pytest.raises(
        Exception,
        match='openmetrics_endpoint: {} is incorrectly configured'.format(endpoint),
    ):
        check = AwsNeuronCheck('aws_neuron', {}, [{'openmetrics_endpoint': endpoint}])
        dd_run_check(check)
