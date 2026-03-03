# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from unittest import mock

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tagging import tagger

FIXTURES_PATH = Path(__file__).parent / 'fixtures'


POD_UID = 'aabbccdd-1234-5678-abcd-ef0123456789'
K8S_TAGS = ['pod_name:my-pod', 'kube_namespace:default', 'kube_deployment:my-app']

EXPECTED_METRICS = [
    'kata.hypervisor_fds',
    'kata.hypervisor_io_stats_read_bytes',
    'kata.hypervisor_io_stats_write_bytes',
    'kata.hypervisor_threads',
    'kata.hypervisor_vcpus',
    'kata.hypervisor_vm_rss_bytes',
]


@pytest.fixture
def run_check_with_sandbox(dd_run_check, mock_http_response, make_check, make_sandbox_mocks):
    """Factory fixture — runs the check end-to-end against a single sandbox.

    Returns the check instance so callers can inspect internal state if needed.
    """

    def _run(sandbox_id='abc123', storage_path='/run/vc/sbs', instance_config=None):
        check = make_check(instance_config)
        mock_exists, mock_listdir, mock_isdir, _ = make_sandbox_mocks(sandbox_id, storage_path)
        mock_http_response(file_path=FIXTURES_PATH / 'sandbox_metrics.txt')

        with (
            mock.patch('os.path.exists', side_effect=mock_exists),
            mock.patch('os.listdir', side_effect=mock_listdir),
            mock.patch('os.path.isdir', side_effect=mock_isdir),
            mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
        ):
            dd_run_check(check)

        return check

    return _run


def test_check_collects_all_shim_metrics(aggregator, run_check_with_sandbox):
    """All metrics exposed by the shim endpoint are scraped and submitted."""
    run_check_with_sandbox()

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)


def test_check_metrics_carry_sandbox_id_tag(aggregator, run_check_with_sandbox):
    sandbox_id = 'my-sandbox-42'
    run_check_with_sandbox(sandbox_id=sandbox_id)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, f'sandbox_id:{sandbox_id}')


def test_check_metrics_carry_instance_level_tags(aggregator, run_check_with_sandbox):
    # Use non-generic tag names to avoid the GENERIC_TAGS validation check in the stubs.
    run_check_with_sandbox(instance_config={'tags': ['team:platform', 'region:us-east']})

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, 'team:platform')
        aggregator.assert_metric_has_tag(metric, 'region:us-east')



def test_check_running_shim_count_reflects_number_of_discovered_sandboxes(aggregator, run_check_with_sandbox):
    run_check_with_sandbox()

    aggregator.assert_metric('kata.running_shim_count', value=1)


def test_check_scrapes_metrics_from_all_sandboxes(dd_run_check, aggregator, mock_http_response, make_check):
    """With two live sandboxes, each gets its own scrape and distinct sandbox_id tags."""
    sandbox_a, sandbox_b = 'sandbox-aaa', 'sandbox-bbb'
    storage_path = '/run/vc/sbs'
    socket_a = f'{storage_path}/{sandbox_a}/shim-monitor.sock'
    socket_b = f'{storage_path}/{sandbox_b}/shim-monitor.sock'

    check = make_check()
    mock_http_response(file_path=FIXTURES_PATH / 'sandbox_metrics.txt')

    with (
        mock.patch('os.path.exists', side_effect=lambda p: p in [storage_path, socket_a, socket_b]),
        mock.patch('os.listdir', side_effect=lambda p: [sandbox_a, sandbox_b] if p == storage_path else []),
        mock.patch(
            'os.path.isdir',
            side_effect=lambda p: p in [f'{storage_path}/{sandbox_a}', f'{storage_path}/{sandbox_b}'],
        ),
        mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
    ):
        dd_run_check(check)

    aggregator.assert_metric('kata.running_shim_count', value=2)
    aggregator.assert_metric_has_tag('kata.hypervisor_vcpus', f'sandbox_id:{sandbox_a}')
    aggregator.assert_metric_has_tag('kata.hypervisor_vcpus', f'sandbox_id:{sandbox_b}')


def test_check_metrics_carry_k8s_tags_when_cri_resolves_pod(
    dd_run_check, aggregator, mock_http_response, make_check, make_sandbox_mocks
):
    """When the CRI client resolves a pod UID and the tagger has K8s tags, they propagate to every metric."""
    sandbox_id = 'k8s-sandbox'
    tagger.set_tags({'kubernetes_pod_uid://' + POD_UID: K8S_TAGS})

    check = make_check()
    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID
    check._cri_client = mock_cri

    mock_exists, mock_listdir, mock_isdir, _ = make_sandbox_mocks(sandbox_id)
    mock_http_response(file_path=FIXTURES_PATH / 'sandbox_metrics.txt')

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
    ):
        dd_run_check(check)

    for k8s_tag in K8S_TAGS:
        aggregator.assert_metric_has_tag('kata.hypervisor_vcpus', k8s_tag)


def test_check_emits_critical_service_check_when_shim_socket_unreachable(
    dd_run_check, aggregator, make_check, make_sandbox_mocks
):
    """A connection failure to the shim socket emits openmetrics.health CRITICAL."""
    sandbox_id = 'unreachable-sandbox'
    check = make_check()
    mock_exists, mock_listdir, mock_isdir, _ = make_sandbox_mocks(sandbox_id)

    with (
        mock.patch(
            'datadog_checks.base.utils.http.RequestsWrapper.get',
            side_effect=RequestsConnectionError('socket unreachable'),
        ),
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
        pytest.raises(Exception, match='There was an error scraping endpoint'),
    ):
        dd_run_check(check)

    aggregator.assert_service_check('kata.openmetrics.health', status=AgentCheck.CRITICAL)


def test_check_emits_critical_service_check_on_http_error_response(
    dd_run_check, aggregator, mock_http_response, make_check, make_sandbox_mocks
):
    """An HTTP error response (e.g. 503) from the shim endpoint emits openmetrics.health CRITICAL."""
    sandbox_id = 'error-sandbox'
    check = make_check()
    mock_exists, mock_listdir, mock_isdir, _ = make_sandbox_mocks(sandbox_id)
    mock_http_response(status_code=503)

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
        pytest.raises(Exception),
    ):
        dd_run_check(check)

    aggregator.assert_service_check('kata.openmetrics.health', status=AgentCheck.CRITICAL)


def test_check_succeeds_with_no_service_checks_when_no_sandboxes_found(dd_run_check, aggregator, make_check):
    """When no sandboxes are discovered, the check completes without emitting any health service checks."""
    check = make_check()

    with (
        mock.patch('os.path.exists', return_value=False),
        mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
    ):
        dd_run_check(check)

    aggregator.assert_metric('kata.running_shim_count', value=0)
    assert len(aggregator.service_checks('kata.openmetrics.health')) == 0
