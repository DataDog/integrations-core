# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.nvidia_triton import NvidiaTritonCheck

from .common import METRICS_MOCK, get_fixture_path

pytestmark = pytest.mark.unit


def test_check_metrics_nvidia_triton(dd_run_check, aggregator, instance_metrics, mock_http_response):
    """
    Use static files for the metrics and version tests.
    """

    check = NvidiaTritonCheck('nvidia_triton', {}, [instance_metrics])
    mock_http_response(file_path=get_fixture_path('metrics/metrics'))
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(name=metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.OK)


def test_emits_critical_openemtrics_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, mock_http_response
):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http_response(status_code=404)
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.CRITICAL)


def test_emits_critical_api_service_check_when_service_is_down(aggregator, instance, mock_http_response):
    """
    If we fail to reach the API endpoint the health service check should report as critical
    """
    mock_http_response(status_code=404)
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    check._check_server_health()

    aggregator.assert_service_check('nvidia_triton.health.status', ServiceCheck.CRITICAL)


def test_check_nvidia_triton_metadata(datadog_agent, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('info/v2'))
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])

    check.check_id = 'test:123'
    check._submit_version_metadata()
    raw_version = '2.38.0'

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
        'version.scheme': 'semver',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:16 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert NvidiaTritonCheck.DEFAULT_METRIC_LIMIT == 0


def test_default_server_port_is_8000():
    # Kills the core/NumberReplacer mutants at check.py:27 (server_port default 8000 -> 8001/7999).
    check = NvidiaTritonCheck('nvidia_triton', {}, [{"openmetrics_endpoint": "http://localhost:9090/metrics"}])
    assert check.server_port == '8000'


def test_submit_version_metadata_skipped_when_metadata_collection_disabled(datadog_agent, instance, mock_http_response):
    # Kills the core/RemoveDecorator mutant at check.py:51 (removing @AgentCheck.metadata_entrypoint would
    # make the method run even though metadata collection is disabled).
    mock_http_response(file_path=get_fixture_path('info/v2'))
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    check.check_id = 'test:disabled-collection'
    datadog_agent._config['enable_metadata_collection'] = False
    check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)


def test_submit_version_metadata_ignores_extra_version_segments(datadog_agent, instance, mock_http_response):
    # Kills the ReplaceComparisonOperator_GtE_Eq and ReplaceComparisonOperator_GtE_LtE mutants at check.py:60
    # (`len(version_split) >= 3` -> `== 3` / `<= 3`), which would treat a 4-segment version as malformed.
    mock_http_response(json_data={"version": "1.2.3.4"})
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    check.check_id = 'test:extra-segment'
    check._submit_version_metadata()

    datadog_agent.assert_metadata(
        'test:extra-segment',
        {
            'version.major': '1',
            'version.minor': '2',
            'version.patch': '3',
            'version.raw': '1.2.3',
            'version.scheme': 'semver',
        },
    )


def test_submit_version_metadata_skips_when_too_few_segments(datadog_agent, instance, mock_http_response):
    # Kills the core/NumberReplacer mutant at check.py:60 (`>= 3` -> `>= 2`), which would raise an
    # IndexError on a 2-segment version instead of treating it as malformed.
    mock_http_response(json_data={"version": "1.2"})
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    check.check_id = 'test:short-segment'
    check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)


@pytest.mark.parametrize(
    'status_code, expect_critical, expect_ok',
    [
        (199, False, False),  # kills the core/NumberReplacer mutant at check.py:85 (200 -> 199)
        (200, False, True),
        (201, False, False),  # kills ReplaceComparisonOperator_Eq_GtE at check.py:85 (== 200 -> >= 200)
        (300, False, False),  # kills ReplaceComparisonOperator_LtE_IsNot/NotEq, ReplaceAndWithOr at check.py:83
        (399, False, False),  # kills the core/NumberReplacer mutant at check.py:83 (400 -> 399)
        (400, True, False),  # kills ReplaceComparisonOperator_LtE_Lt, core/NumberReplacer (400 -> 401) at check.py:83
        (599, True, False),  # kills the core/NumberReplacer mutant at check.py:83 (600 -> 599)
        (600, False, False),  # kills ReplaceComparisonOperator_Lt_LtE, core/NumberReplacer (600 -> 601) at check.py:83
        (700, False, False),  # kills ReplaceComparisonOperator_Lt_NotEq at check.py:83
    ],
)
def test_check_server_health_status_code_boundaries(
    status_code, expect_critical, expect_ok, instance, aggregator, mock_http_response
):
    mock_http_response(status_code=status_code)
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    check._check_server_health()

    aggregator.assert_service_check(
        'nvidia_triton.health.status', ServiceCheck.CRITICAL, count=1 if expect_critical else 0
    )
    aggregator.assert_service_check('nvidia_triton.health.status', ServiceCheck.OK, count=1 if expect_ok else 0)
    aggregator.assert_service_check('nvidia_triton.health.status', ServiceCheck.UNKNOWN, count=0 if expect_ok else 1)
