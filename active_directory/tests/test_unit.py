# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest

from datadog_checks.active_directory.check import ActiveDirectoryCheckV2
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_windows
from datadog_checks.dev.utils import get_metadata_metrics

# Import the mock data we will use for our tests
from .common import MOCK_INSTANCES, PERFORMANCE_OBJECTS

pytestmark = [requires_windows]


def mock_expand_counter_path(wildcard_path):
    """
    This helper replaces the problematic `ExpandCounterPath`.
    It satisfies the base check's instance discovery mechanism.
    """
    object_name = wildcard_path.strip("\\").split("(")[0]
    if object_name in MOCK_INSTANCES:
        return [f"\\{object_name}({instance})\\" for instance in MOCK_INSTANCES[object_name]]
    return []


@pytest.fixture
def mock_service_states(mocker):
    """
    Mocks the check's _is_service_running method directly.
    """
    created_mocks = {}

    def _mock_services(service_states):
        def is_running_mock(service_name):
            return service_states.get(service_name, True)

        service_mock = mocker.patch(
            'datadog_checks.active_directory.check.ActiveDirectoryCheckV2._is_service_running',
            side_effect=is_running_mock,
        )
        created_mocks['service_mock'] = service_mock
        return created_mocks

    return _mock_services


def test_all_services_running(aggregator, dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test metric collection when all services are running."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)
    mock_service_states({'NTDS': True, 'Netlogon': True, 'DHCPServer': True, 'DFSR': True})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])
    dd_run_check(check)

    global_tags = ['server:laptop-e5eb8phe']
    aggregator.assert_service_check('active_directory.windows.perf.health', ServiceCheck.OK, count=1)

    # Assert all metrics are collected with correct values and instance tags
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', 9000, global_tags + ['instance:NTDS'])
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 9000, global_tags + ['instance:lab.local'])
    aggregator.assert_metric(
        'active_directory.security.kerberos_authentications', 9000, global_tags + ['instance:Security']
    )
    aggregator.assert_metric(
        'active_directory.dhcp.failover.messages_received', 9000, global_tags + ['instance:DHCPServer']
    )
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', 9000, global_tags + ['instance:InstanceOne'])
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', 42, global_tags + ['instance:InstanceTwo'])

    # aggregator.assert_all_metrics_covered()


def test_only_required_services(aggregator, dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test that only NTDS metrics are collected when optional services are stopped."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)
    mock_service_states({'NTDS': True, 'Netlogon': False, 'DHCPServer': False, 'DFSR': False})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])
    dd_run_check(check)

    # Assert NTDS metrics are collected
    aggregator.assert_metric(
        'active_directory.dra.inbound.bytes.total', 9000, ['server:laptop-e5eb8phe', 'instance:NTDS']
    )

    # Assert other metrics are NOT collected
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', count=0)
    aggregator.assert_metric('active_directory.security.kerberos_authentications', count=0)
    aggregator.assert_metric('active_directory.dhcp.failover.messages_received', count=0)
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', count=0)


def test_mixed_service_states(aggregator, dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test selective metric collection based on service states."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)
    mock_service_states({'NTDS': True, 'Netlogon': True, 'DHCPServer': False, 'DFSR': False})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])
    dd_run_check(check)

    # Assert that metrics for running services are collected
    aggregator.assert_metric(
        'active_directory.netlogon.semaphore_waiters', 9000, ['server:laptop-e5eb8phe', 'instance:lab.local']
    )

    # Assert that metrics for stopped services are NOT collected
    aggregator.assert_metric('active_directory.dhcp.packets_received_sec', count=0)


def test_service_check_disabled(aggregator, dd_run_check, mock_performance_objects, mocker):
    """Test all metrics are collected when service_check_enabled=False."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)

    instance = {'host': 'laptop-e5eb8phe', 'service_check_enabled': False}
    check = ActiveDirectoryCheckV2("active_directory", {}, [instance])
    dd_run_check(check)

    # Assert ALL metrics are collected, regardless of mocked service state
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', at_least=1)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', at_least=1)
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', at_least=1)


def test_force_all_metrics(aggregator, dd_run_check, mock_performance_objects, mocker):
    """Test all metrics are collected when force_all_metrics=True."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)

    instance = {'host': 'laptop-e5eb8phe', 'force_all_metrics': True}
    check = ActiveDirectoryCheckV2("active_directory", {}, [instance])
    dd_run_check(check)

    # Assert ALL metrics are collected, regardless of mocked service state
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', at_least=1)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', at_least=1)
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', at_least=1)


def test_service_state_caching(dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test that service states are cached and reused."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)
    mocks = mock_service_states({'NTDS': True})
    is_running_mock = mocks['service_mock']

    instance = {'host': 'laptop-e5eb8phe', 'service_cache_duration': 300}
    check = ActiveDirectoryCheckV2("active_directory", {}, [instance])

    # First run
    dd_run_check(check)
    first_call_count = is_running_mock.call_count
    assert first_call_count > 0

    # Second run from cache
    dd_run_check(check)
    assert is_running_mock.call_count == first_call_count

    # Third run after cache expiration
    check._last_service_check = time.time() - 301
    dd_run_check(check)
    assert is_running_mock.call_count > first_call_count


def test_metadata_metrics(aggregator, dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test that check respects metadata definitions."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)
    mock_service_states(dict.fromkeys(MOCK_INSTANCES, True))

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])
    dd_run_check(check)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
