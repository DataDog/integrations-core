# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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
    Mocks the _get_windows_service_state function.
    """
    import win32service

    created_mocks = {}

    def _mock_services(service_states):
        def service_state_mock(service_name):
            # Return SERVICE_RUNNING (4) if service should be running, SERVICE_STOPPED (1) otherwise
            is_running = service_states.get(service_name, True)
            return win32service.SERVICE_RUNNING if is_running else win32service.SERVICE_STOPPED

        service_mock = mocker.patch(
            'datadog_checks.active_directory.check._get_windows_service_state',
            side_effect=service_state_mock,
        )
        created_mocks['service_mock'] = service_mock
        return created_mocks

    return _mock_services


def test_all_services_running(
    aggregator, dd_run_check, mock_performance_objects, mock_service_states, dd_default_hostname
):
    """Test metric collection when all services are running."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mock_service_states({'NTDS': True, 'Netlogon': True, 'DHCPServer': True, 'DFSR': True})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": dd_default_hostname}])
    dd_run_check(check)

    global_tags = ['server:{}'.format(dd_default_hostname)]
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


def test_no_running_services(aggregator, dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test that no metrics are collected when no services are running."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mock_service_states({'NTDS': False, 'Netlogon': False, 'DHCPServer': False, 'DFSR': False})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])
    dd_run_check(check)

    # Assert no AD metrics are collected when services are stopped
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', count=0)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', count=0)
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', count=0)


def test_service_exception_handling(aggregator, dd_run_check, mock_performance_objects, mocker):
    """Test behavior when service state checking fails."""
    mock_performance_objects(PERFORMANCE_OBJECTS)

    # Mock the service state function to raise an exception
    mocker.patch(
        'datadog_checks.active_directory.check._get_windows_service_state',
        side_effect=Exception("Service query failed"),
    )

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])

    # Should not crash, but will collect no metrics due to exception
    dd_run_check(check)

    # Should have no metrics due to service query failure
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', count=0)


def test_service_state_querying(dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test that service states are queried on each run."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mocks = mock_service_states({'NTDS': True})
    service_state_mock = mocks['service_mock']

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])

    # First run
    dd_run_check(check)
    first_call_count = service_state_mock.call_count
    assert first_call_count > 0

    # Second run should query services again (no caching)
    dd_run_check(check)
    assert service_state_mock.call_count > first_call_count


def test_metadata_metrics(aggregator, dd_run_check, mock_performance_objects, mock_service_states, mocker):
    """Test that check respects metadata definitions."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    # apply_pdh_patch(mocker)
    mock_service_states(dict.fromkeys(MOCK_INSTANCES, True))

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": 'laptop-e5eb8phe'}])
    dd_run_check(check)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
