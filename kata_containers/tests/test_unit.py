# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict  # noqa: F401
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
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
def test_check_with_sandbox(dd_run_check, aggregator, instance, sandbox_id):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any], str) -> None
    """Test check with a running sandbox."""
    check = KataContainersCheck('kata_containers', {}, [instance])

    socket_path = f'/run/vc/sbs/{sandbox_id}/shim-monitor.sock'

    def mock_exists(path):
        if path in ['/run/vc/sbs', socket_path]:
            return True
        return False

    def mock_listdir(path):
        if path == '/run/vc/sbs':
            return [sandbox_id]
        return []

    def mock_isdir(path):
        return path == f'/run/vc/sbs/{sandbox_id}'

    mock_response = mock.Mock()
    mock_response.text = SAMPLE_METRICS
    mock_response.raise_for_status = mock.Mock()

    # Mock the datadog_checks.base.utils.http.RequestsWrapper.get method
    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.base.utils.http.RequestsWrapper.get', return_value=mock_response),
    ):
        dd_run_check(check)

    # Check that we found the sandbox
    aggregator.assert_metric('kata.running_shim_count', value=1)

    # Check that metrics were collected
    expected_tags = [f'sandbox_id:{sandbox_id}']
    aggregator.assert_metric('kata.hypervisor_fds', value=10, tags=expected_tags)
    aggregator.assert_metric('kata.hypervisor_threads', value=5, tags=expected_tags)
    aggregator.assert_metric('kata.shim_fds', value=15, tags=expected_tags)
    aggregator.assert_metric('kata.shim_threads', value=3, tags=expected_tags)
    aggregator.assert_metric('kata.shim_pod_overhead_cpu', value=0.5, tags=expected_tags)
    aggregator.assert_metric('kata.shim_pod_overhead_memory_in_bytes', value=104857600, tags=expected_tags)
    aggregator.assert_metric('kata.agent_scrape_count', value=100, tags=expected_tags)

    # Check service check
    aggregator.assert_service_check('kata.can_connect', status=AgentCheck.OK, tags=expected_tags)


def test_check_socket_connection_failure(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    """Test check when socket connection fails."""
    check = KataContainersCheck('kata_containers', {}, [instance])

    sandbox_id = 'failing-sandbox'
    socket_path = f'/run/vc/sbs/{sandbox_id}/shim-monitor.sock'

    def mock_exists(path):
        if path in ['/run/vc/sbs', socket_path]:
            return True
        return False

    def mock_listdir(path):
        if path == '/run/vc/sbs':
            return [sandbox_id]
        return []

    def mock_isdir(path):
        return path == f'/run/vc/sbs/{sandbox_id}'

    # Mock the HTTP wrapper's get method to raise an exception
    with (
        mock.patch('os.path.exists', side_effect=mock_exists),
        mock.patch('os.listdir', side_effect=mock_listdir),
        mock.patch('os.path.isdir', side_effect=mock_isdir),
        mock.patch('datadog_checks.base.utils.http.RequestsWrapper.get', side_effect=Exception('Connection failed')),
    ):
        dd_run_check(check)

    # Should still report the sandbox count
    aggregator.assert_metric('kata.running_shim_count', value=1)

    # Should report connection failure
    expected_tags = [f'sandbox_id:{sandbox_id}']
    aggregator.assert_service_check('kata.can_connect', status=AgentCheck.CRITICAL, tags=expected_tags)
