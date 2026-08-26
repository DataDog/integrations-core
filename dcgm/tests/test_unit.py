# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from types import SimpleNamespace
from unittest import mock

import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dcgm import DcgmCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRICS

pytestmark = pytest.mark.unit


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:11 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert DcgmCheck.DEFAULT_METRIC_LIMIT == 0


def test_add_build_version_to_metadata_iterates_sample_data(check):
    # Kills the core/ZeroIterationForLoop mutant at check.py:29 (sample_data -> []).
    sample = SimpleNamespace(labels={'build_version': '2_1_3'})
    with mock.patch.object(check, 'set_metadata') as set_metadata:
        check._add_build_version_to_metadata(None, [(sample, [], None)], None)
    set_metadata.assert_called_once_with('version', '2.1.3')


def test_critical_service_check(dd_run_check, aggregator, mock_http_response, check):
    """
    When we can't connect to dcgm-exporter for whatever reason we should only submit a CRITICAL service check.
    """
    mock_http_response(status_code=404)
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', status=check.CRITICAL)


@pytest.mark.usefixtures("mock_label_remap")
def test_label_remap(dd_run_check, aggregator, check):
    """
    Test that Prometheus labels are remapped and autodiscovery tags for the
    exporter pod's namespace/pod/container are filtered out via ignore_tags.
    """
    # First run to initialize scrapers
    dd_run_check(check)
    aggregator.reset()

    # Simulate autodiscovery adding tags for the exporter pod itself
    check.set_dynamic_tags(
        'kube_namespace:gpu-operator',
        'pod_name:nvidia-dcgm-exporter-abc',
        'kube_container_name:nvidia-dcgm-exporter',
    )
    dd_run_check(check)

    aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)

    aggregator.assert_metric(
        'dcgm.gpu_utilization',
        tags=[
            'DCGM_FI_DRIVER_VERSION:460.106.00',
            'DCGM_FI_PROCESS_NAME:/usr/bin/dcgm-exporter',
            'Hostname:424773df46e0',
            'UUID:GPU-20c56d28-0da5-6d26-a36a-e7af1ce2586e',
            'device:nvidia0',
            'endpoint:http://localhost:9400/metrics',
            'gpu:0',
            'kube_container_name:baz',
            'kube_namespace:foo',
            'modelName:Tesla T4',
            'pod_name:bar',
        ],
    )


@pytest.mark.usefixtures("mock_metrics")
def test_successful_run(dd_run_check, aggregator, check):
    dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)
    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(name=metric)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_invalid_config():
    """
    Config with unknown fields should raise an exception.
    """
    check = DcgmCheck('dcgm', {}, [{'bad_config_option': 'test'}])
    with pytest.raises(ConfigurationError):
        check.load_configuration_models()
