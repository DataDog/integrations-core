# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.aws_neuron import AwsNeuronCheck

from .common import TEST_METRICS, RENAMED_LABELS, get_fixture_path


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('aws_neuron_metrics.txt'))

    check = AwsNeuronCheck('aws_neuron', {}, [instance])
    dd_run_check(check)

    for metric in TEST_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

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
    instance = {'openmetrics_endpoint': 'aws_neuron:2112/metrics'}
    for k, v in instance.items():
        with pytest.raises(
            Exception,
            match=f'{k}: {v} is incorrectly configured',
        ):
            check = AwsNeuronCheck('aws_neuron', {}, [instance])
            dd_run_check(check)


def test_rename_labels(dd_run_check, instance, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('rename_labels.txt'))
    check = AwsNeuronCheck('aws_neuron', {}, [instance])
    dd_run_check(check)
    for tag in RENAMED_LABELS:
        aggregator.assert_metric_has_tag("aws_neuron.python_info", tag)
