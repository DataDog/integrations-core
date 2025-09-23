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
    Mocks the _service_exists function.
    """

    def _mock_services(service_states):
        def service_exists_mock(service_name):
            return service_states.get(service_name, True)

        return mocker.patch('datadog_checks.active_directory.check._service_exists', side_effect=service_exists_mock)

    return _mock_services


def test_all_services_existing(
    aggregator, dd_run_check, mock_performance_objects, mock_service_states, dd_default_hostname
):
    """Test metric collection when all services exist."""
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
        'active_directory.dhcp.failover.binding_updates_received', 9000, global_tags + ['instance:DHCPServer']
    )
    aggregator.assert_metric('active_directory.dfsr.deleted_space_in_use', 9000, global_tags + ['instance:InstanceOne'])
    aggregator.assert_metric('active_directory.dfsr.deleted_space_in_use', 42, global_tags + ['instance:InstanceTwo'])


def test_only_required_services(
    aggregator, dd_run_check, mock_performance_objects, mock_service_states, dd_default_hostname
):
    """Test that only NTDS metrics are collected when optional services don't exist."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mock_service_states({'NTDS': True, 'Netlogon': False, 'DHCPServer': False, 'DFSR': False})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": dd_default_hostname}])
    dd_run_check(check)
    global_tags = ['server:{}'.format(dd_default_hostname)]

    # Assert NTDS metrics are collected
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', 9000, global_tags + ['instance:NTDS'])

    # Assert other metrics are NOT collected
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', count=0)
    aggregator.assert_metric('active_directory.security.kerberos_authentications', count=0)
    aggregator.assert_metric('active_directory.dhcp.failover.binding_updates_received', count=0)
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', count=0)


def test_mixed_service_states(
    aggregator, dd_run_check, mock_performance_objects, mock_service_states, dd_default_hostname
):
    """Test selective metric collection based on service existence."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mock_service_states({'NTDS': True, 'Netlogon': True, 'DHCPServer': False, 'DFSR': False})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": dd_default_hostname}])
    dd_run_check(check)
    global_tags = ['server:{}'.format(dd_default_hostname)]

    # Assert that metrics for existing services are collected
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', 9000, global_tags + ['instance:NTDS'])
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 9000, global_tags + ['instance:lab.local'])
    aggregator.assert_metric(
        'active_directory.security.kerberos_authentications', 9000, global_tags + ['instance:Security']
    )

    # Assert that metrics for non-existing services are NOT collected
    aggregator.assert_metric('active_directory.dhcp.failover.binding_updates_received', count=0)
    aggregator.assert_metric('active_directory.dfsr.deleted_space_in_use', count=0)


def test_no_existing_services(
    aggregator, dd_run_check, mock_performance_objects, mock_service_states, dd_default_hostname
):
    """Test that no metrics are collected when no services exist."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mock_service_states({'NTDS': False, 'Netlogon': False, 'DHCPServer': False, 'DFSR': False})

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": dd_default_hostname}])
    dd_run_check(check)

    # Assert no AD metrics are collected when services don't exist
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', count=0)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', count=0)
    aggregator.assert_metric('active_directory.security.kerberos_authentications', count=0)
    aggregator.assert_metric('active_directory.dhcp.failover.binding_updates_received', count=0)
    aggregator.assert_metric('active_directory.dfsr.deleted_space_in_use', count=0)


def test_metadata_metrics(aggregator, dd_run_check, mock_performance_objects, mock_service_states, dd_default_hostname):
    """Test that check respects metadata definitions."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mock_service_states(dict.fromkeys(MOCK_INSTANCES, True))

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": dd_default_hostname}])
    dd_run_check(check)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
