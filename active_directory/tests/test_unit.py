# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from unittest import mock

from datadog_checks.active_directory.check import ActiveDirectoryCheckV2
from datadog_checks.base.constants import ServiceCheck

# --- Fixtures ---

@pytest.fixture
def core_performance_objects():
    """Provides a mock for core NTDS performance counters that are always collected."""
    return {
        'NTDS': (
            [None],  # NTDS is a global object with no instances
            {
                'DS Threads in Use': [5],
                'LDAP Client Sessions': [10],
                'LDAP Bind Time': [50],
                'LDAP Successful Binds/sec': [20],
                'LDAP Searches/sec': [100],
                'LDAP Writes/sec': [15],
                'LDAP Active Threads': [4],
                'DS Client Binds/sec': [25],
                'DRA Pending Replication Synchronizations': [0],
            },
        )
    }

@pytest.fixture
def optional_performance_objects():
    """Mock performance objects for optional, service-dependent components."""
    return {
        'Netlogon': (
            ['_Total'],
            {
                'Semaphore Waiters': [2],
                'Semaphore Holders': [1],
            },
        ),
        'Security System-Wide Statistics': (
            ['_Total'],
            {
                'NTLM Authentications': [50],
                'Kerberos Authentications': [200],
            },
        ),
        'DHCP Server': (
            ['_Total'],
            {
                'Binding Updates Dropped': [15],
                'Failover: Update pending messages': [3],
            },
        ),
        'DFS Replicated Folders': (
            ['Domain System Volume', 'Public Share'],
            {
                'Staging Space In Use': [5242880, 10485760],
                'Conflict Folder Size': [524288, 1048576],
            },
        ),
    }

# --- Test Cases ---

def test_core_ntds_metrics(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects, core_performance_objects):
    """
    Tests the collection of required NTDS metrics, which should always be collected
    regardless of service availability.
    """
    mock_performance_objects(core_performance_objects)
    check = ActiveDirectoryCheckV2('active_directory', {}, [{'host': dd_default_hostname}])
    dd_run_check(check)

    global_tags = [f'server:{dd_default_hostname}']
    
    aggregator.assert_service_check('active_directory.windows.perf.health', ServiceCheck.OK, tags=global_tags)
    aggregator.assert_metric('active_directory.ntds.ds.threads_in_use', 5, tags=global_tags)
    aggregator.assert_metric('active_directory.ntds.ldap.client_sessions', 10, tags=global_tags)
    aggregator.assert_metric('active_directory.ntds.ldap.bind_time', 50, tags=global_tags)
    
    aggregator.assert_all_metrics_covered()

@mock.patch('datadog_checks.active_directory.check.ActiveDirectoryCheckV2._is_service_running', return_value=True)
def test_optional_metrics_when_services_are_running(mock_is_service_running, aggregator, dd_default_hostname, dd_run_check, mock_performance_objects, optional_performance_objects):
    """
    Tests that all optional metrics are collected when their corresponding services are detected as running.
    """
    mock_performance_objects(optional_performance_objects)
    check = ActiveDirectoryCheckV2('active_directory', {}, [{'host': dd_default_hostname}])
    dd_run_check(check)

    global_tags = [f'server:{dd_default_hostname}']
    total_instance_tags = global_tags + ['instance:_Total']

    # Assert Netlogon & Security metrics (controlled by 'Netlogon' service)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 2, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.security.ntlm_authentications', 50, tags=total_instance_tags)

    # Assert DHCP metrics (controlled by 'DNS' service in the check - assuming DHCP is on the DNS server)
    aggregator.assert_metric('active_directory.dhcp.binding_updates_dropped', 15, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.dhcp.failover.update_pending_messages', 3, tags=total_instance_tags)

    # Assert DFSR metrics (controlled by 'DFSR' service)
    domain_tags = global_tags + ['replication_group:Domain System Volume']
    public_tags = global_tags + ['replication_group:Public Share']
    aggregator.assert_metric('active_directory.dfsr.staging_folder_size', 5242880, tags=domain_tags)
    aggregator.assert_metric('active_directory.dfsr.conflict_folder_size', 1048576, tags=public_tags)

@mock.patch('datadog_checks.active_directory.check.ActiveDirectoryCheckV2._is_service_running')
def test_service_aware_collection_skips_metrics(mock_is_service_running, aggregator, dd_default_hostname, dd_run_check, mock_performance_objects, core_performance_objects, optional_performance_objects):
    """
    Tests that metric collection is dynamically skipped if a service is not running.
    """
    all_performance_objects = {**core_performance_objects, **optional_performance_objects}
    mock_performance_objects(all_performance_objects)

    # Configure the mock to simulate that the DFSR service is NOT running
    def service_side_effect(service_name):
        return service_name != 'DFSR'  # Return True for all services except DFSR
    mock_is_service_running.side_effect = service_side_effect

    check = ActiveDirectoryCheckV2('active_directory', {}, [{'host': dd_default_hostname}])
    dd_run_check(check)

    # NTDS metrics should ALWAYS be collected (it's a required metric set)
    aggregator.assert_metric('active_directory.ntds.ds.threads_in_use', 5, count=1)
    
    # Netlogon metrics SHOULD be collected (service is mocked as running)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 2, count=1)
    
    # DFSR metrics should NOT be collected (service is mocked as not running)
    aggregator.assert_metric('active_directory.dfsr.staging_folder_size', count=0)

@mock.patch('datadog_checks.active_directory.check.ActiveDirectoryCheckV2._is_service_running')
def test_emits_service_checks(mock_is_service_running, aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    """
    Tests that service checks are emitted correctly based on service status.
    """
    mock_performance_objects({})  # No metrics needed for this test

    # Simulate Netlogon running and DFSR not running
    def service_side_effect(service_name):
        return service_name == 'Netlogon'
    mock_is_service_running.side_effect = service_side_effect

    instance_config = [{'host': dd_default_hostname, 'emit_service_status': True}]
    check = ActiveDirectoryCheckV2('active_directory', {}, instance_config)
    dd_run_check(check)

    global_tags = [f'server:{dd_default_hostname}']

    # Assert that the Netlogon service check is OK
    aggregator.assert_service_check('active_directory.service.netlogon', ServiceCheck.OK, tags=global_tags)
    
    # Assert that the DFSR service check is WARNING (since it's not running)
    aggregator.assert_service_check('active_directory.service.dfsr', ServiceCheck.WARNING, tags=global_tags)