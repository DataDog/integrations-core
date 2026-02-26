# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict  # noqa: F401
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.utils.tagging import tagger
from datadog_checks.kata_containers import KataContainersCheck

SAMPLE_METRICS = """# HELP kata_hypervisor_fds Number of file descriptors
# TYPE kata_hypervisor_fds gauge
kata_hypervisor_fds 10
# HELP kata_hypervisor_threads Number of threads
# TYPE kata_hypervisor_threads gauge
kata_hypervisor_threads 5
# HELP kata_shim_fds Number of file descriptors
# TYPE kata_shim_fds gauge
kata_shim_fds 15
# HELP kata_shim_threads Number of threads
# TYPE kata_shim_threads gauge
kata_shim_threads 3
# HELP kata_shim_pod_overhead_cpu CPU overhead
# TYPE kata_shim_pod_overhead_cpu gauge
kata_shim_pod_overhead_cpu 0.5
# HELP kata_shim_pod_overhead_memory_in_bytes Memory overhead in bytes
# TYPE kata_shim_pod_overhead_memory_in_bytes gauge
kata_shim_pod_overhead_memory_in_bytes 104857600
# HELP kata_agent_scrape_count Agent scrape count
# TYPE kata_agent_scrape_count counter
kata_agent_scrape_count 100
"""

POD_UID = 'aabbccdd-1234-5678-abcd-ef0123456789'
K8S_TAGS = ['pod_name:my-pod', 'kube_namespace:default', 'kube_deployment:my-app']


@pytest.fixture(autouse=True)
def reset_tagger():
    """Ensure tagger state is clean between tests."""
    tagger.reset()
    yield
    tagger.reset()


def _make_sandbox_mocks(sandbox_id: str, storage_path: str = '/run/vc/sbs'):
    """Return filesystem mock callables for a single sandbox at *storage_path*."""
    socket_path = f'{storage_path}/{sandbox_id}/shim-monitor.sock'

    def mock_exists(path):
        return path in [storage_path, socket_path]

    def mock_listdir(path):
        return [sandbox_id] if path == storage_path else []

    def mock_isdir(path):
        return path == f'{storage_path}/{sandbox_id}'

    return mock_exists, mock_listdir, mock_isdir, socket_path


def _mock_http(check, metrics_text: str):
    """Attach a mock HTTP wrapper to *check* that returns *metrics_text*."""
    mock_response = mock.Mock()
    mock_response.text = metrics_text
    mock_response.raise_for_status = mock.Mock()
    mock_http = mock.Mock()
    mock_http.get.return_value = mock_response
    # AgentCheck.http is a lazy property backed by _http; set the instance attr
    # directly so the property returns our mock without triggering real initialization.
    check._http = mock_http
    return mock_http


def test_check_no_sandboxes(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    """Test check when no sandboxes are found."""
    check = KataContainersCheck('kata_containers', {}, [instance])

    with mock.patch('os.path.exists', return_value=False):
        dd_run_check(check)

    aggregator.assert_metric('kata.running_shim_count', value=0)


@pytest.mark.parametrize(
    'sandbox_id',
    [
        'test-sandbox-123',
        'abc123def456',
    ],
)
def test_check_with_sandbox_no_cri(dd_run_check, aggregator, instance, sandbox_id):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any], str) -> None
    """Test check with a running sandbox and no CRI enrichment available."""
    check = KataContainersCheck('kata_containers', {}, [instance])
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)
    _mock_http(check, SAMPLE_METRICS)

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
    ):
        dd_run_check(check)

    aggregator.assert_metric('kata.running_shim_count', value=1)

    expected_tags = [f'sandbox_id:{sandbox_id}']
    aggregator.assert_metric('kata.hypervisor_fds', value=10, tags=expected_tags)
    aggregator.assert_metric('kata.hypervisor_threads', value=5, tags=expected_tags)
    aggregator.assert_metric('kata.shim_fds', value=15, tags=expected_tags)
    aggregator.assert_metric('kata.shim_threads', value=3, tags=expected_tags)
    aggregator.assert_metric('kata.shim_pod_overhead_cpu', value=0.5, tags=expected_tags)
    aggregator.assert_metric('kata.shim_pod_overhead_memory_in_bytes', value=104857600, tags=expected_tags)
    aggregator.assert_metric('kata.agent_scrape_count_total', value=100, tags=expected_tags)
    aggregator.assert_service_check('kata.can_connect', status=AgentCheck.OK, tags=expected_tags)


def test_check_with_cri_enrichment(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    """Test that CRI lookup adds Kubernetes tags from the tagger to all metrics."""
    sandbox_id = 'enriched-sandbox-abc'
    check = KataContainersCheck('kata_containers', {}, [instance])
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)
    _mock_http(check, SAMPLE_METRICS)

    # Pre-populate the tagger stub with K8s tags for the pod UID.
    tagger.set_tags({'kubernetes_pod_uid://' + POD_UID: K8S_TAGS})

    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.CRIClient', return_value=mock_cri),
    ):
        dd_run_check(check)

    # Metrics should carry both sandbox_id and the K8s tags from the tagger.
    expected_tags = [f'sandbox_id:{sandbox_id}'] + K8S_TAGS
    aggregator.assert_metric('kata.hypervisor_fds', value=10, tags=expected_tags)
    aggregator.assert_metric('kata.shim_fds', value=15, tags=expected_tags)
    aggregator.assert_service_check('kata.can_connect', status=AgentCheck.OK, tags=expected_tags)

    # The CRI client must have been called exactly once (cache hit on subsequent calls).
    mock_cri.get_pod_uid.assert_called_once_with(sandbox_id)


def test_pod_uid_cache(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    """Verify that the pod UID is resolved once and then served from cache on subsequent runs."""
    sandbox_id = 'cached-sandbox'
    check = KataContainersCheck('kata_containers', {}, [instance])
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)
    _mock_http(check, SAMPLE_METRICS)

    tagger.set_tags({'kubernetes_pod_uid://' + POD_UID: K8S_TAGS})

    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.CRIClient', return_value=mock_cri),
    ):
        dd_run_check(check)
        dd_run_check(check)

    # Two check runs but only one CRI call — the second is served from cache.
    mock_cri.get_pod_uid.assert_called_once_with(sandbox_id)


def test_pod_uid_cache_eviction(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    """Verify that cache entries are evicted when a sandbox disappears."""
    sandbox_id = 'evicted-sandbox'
    check = KataContainersCheck('kata_containers', {}, [instance])
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)
    _mock_http(check, SAMPLE_METRICS)

    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = POD_UID

    # First run — sandbox is present, cache is populated.
    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.CRIClient', return_value=mock_cri),
    ):
        dd_run_check(check)

    assert sandbox_id in check._pod_uid_cache

    # Second run — sandbox is gone; cache entry must be evicted.
    with mock.patch('os.path.exists', return_value=False):
        dd_run_check(check)

    assert sandbox_id not in check._pod_uid_cache


def test_cri_failure_is_silent(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    """When CRI returns None the check still runs and emits metrics without K8s tags."""
    sandbox_id = 'no-cri-sandbox'
    check = KataContainersCheck('kata_containers', {}, [instance])
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)
    _mock_http(check, SAMPLE_METRICS)

    mock_cri = mock.Mock(spec=['get_pod_uid', 'close'])
    mock_cri.get_pod_uid.return_value = None  # CRI failure

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.CRIClient', return_value=mock_cri),
    ):
        dd_run_check(check)

    # Metrics are still emitted, just without K8s tags.
    expected_tags = [f'sandbox_id:{sandbox_id}']
    aggregator.assert_metric('kata.hypervisor_fds', value=10, tags=expected_tags)
    aggregator.assert_service_check('kata.can_connect', status=AgentCheck.OK, tags=expected_tags)


def test_check_socket_connection_failure(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    """Test check when socket connection fails."""
    sandbox_id = 'failing-sandbox'
    check = KataContainersCheck('kata_containers', {}, [instance])
    mock_exists, mock_listdir, mock_isdir, _ = _make_sandbox_mocks(sandbox_id)

    mock_http = mock.Mock()
    mock_http.get.side_effect = Exception('Connection failed')
    check._http = mock_http

    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.kata_containers.check.GRPC_AVAILABLE', False),
    ):
        dd_run_check(check)

    aggregator.assert_metric('kata.running_shim_count', value=1)

    expected_tags = [f'sandbox_id:{sandbox_id}']
    aggregator.assert_service_check('kata.can_connect', status=AgentCheck.CRITICAL, tags=expected_tags)
