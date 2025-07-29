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
                # DRA Inbound metrics
                'DRA Inbound Bytes Compressed (Between Sites, After Compression)/sec': [1000],
                'DRA Inbound Bytes Compressed (Between Sites, Before Compression)/sec': [2000],
                'DRA Inbound Bytes Not Compressed (Within Site)/sec': [3000],
                'DRA Inbound Bytes Total/sec': [6000],
                'DRA Inbound Full Sync Objects Remaining': [0],
                'DRA Inbound Objects/sec': [10],
                'DRA Inbound Objects Applied/sec': [8],
                'DRA Inbound Objects Filtered/sec': [2],
                'DRA Inbound Object Updates Remaining in Packet': [0],
                'DRA Inbound Properties Applied/sec': [50],
                'DRA Inbound Properties Filtered/sec': [5],
                'DRA Inbound Properties Total/sec': [55],
                'DRA Inbound Values (DNs only)/sec': [20],
                'DRA Inbound Values Total/sec': [30],
                # DRA Outbound metrics
                'DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec': [500],
                'DRA Outbound Bytes Compressed (Between Sites, Before Compression)/sec': [1000],
                'DRA Outbound Bytes Not Compressed (Within Site)/sec': [2000],
                'DRA Outbound Bytes Total/sec': [3500],
                'DRA Outbound Objects Filtered/sec': [1],
                'DRA Outbound Objects/sec': [5],
                'DRA Outbound Properties/sec': [25],
                'DRA Outbound Values (DNs only)/sec': [10],
                'DRA Outbound Values Total/sec': [15],
                # Other NTDS metrics
                'DRA Pending Replication Synchronizations': [0],
                'DRA Sync Requests Made': [100],
                'DS Threads in Use': [5],
                'LDAP Client Sessions': [10],
                'LDAP Bind Time': [50],
                'LDAP Successful Binds/sec': [20],
                'LDAP Searches/sec': [100],
                'LDAP Writes/sec': [15],
                'LDAP Active Threads': [4],
                'DS Client Binds/sec': [25],
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
                'Semaphore Acquires': [1000],
                'Semaphore Timeouts': [5],
                'Average Semaphore Hold Time': [0.5],
                'Last Authentication Time': [300],
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
                'Failover: Messages received/sec': [10.5],
                'Failover: Messages sent/sec': [12.3],
            },
        ),
        'DFS Replicated Folders': (
            ['Domain System Volume', 'Public Share'],
            {
                'Size of Files Deleted': [1048576, 2097152],
                'Staging Space In Use': [5242880, 10485760],
                'File Installs Retried': [10, 25],
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
    # NTDS metrics that use metric_name don't include the ntds prefix
    aggregator.assert_metric('active_directory.ds.threads_in_use', 5, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.client_sessions', 10, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.bind_time', 50, tags=global_tags)
    
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

    # Assert Netlogon metrics (controlled by 'Netlogon' service)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 2, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_holders', 1, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_acquires', 1000, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_timeouts', 5, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_hold_time', 0.5, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.last_authentication_time', 300, tags=total_instance_tags)
    
    # Assert Security metrics (controlled by 'Netlogon' service)
    aggregator.assert_metric('active_directory.security.ntlm_authentications', 50, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.security.kerberos_authentications', 200, tags=total_instance_tags)

    # Assert DHCP metrics (controlled by 'DHCPServer' service)
    aggregator.assert_metric('active_directory.dhcp.binding_updates_dropped', 15, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.dhcp.failover.update_pending_messages', 3, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.dhcp.failover.messages_received', 10.5, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.dhcp.failover.messages_sent', 12.3, tags=total_instance_tags)

    # Assert DFSR metrics (controlled by 'DFSR' service)
    domain_tags = global_tags + ['replication_group:Domain System Volume']
    public_tags = global_tags + ['replication_group:Public Share']
    
    # Domain System Volume metrics
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', 1048576, tags=domain_tags)
    aggregator.assert_metric('active_directory.dfsr.staging_folder_size', 5242880, tags=domain_tags)
    aggregator.assert_metric('active_directory.dfsr.file_installs_retried', 10, tags=domain_tags)
    aggregator.assert_metric('active_directory.dfsr.conflict_files_size', 524288, tags=domain_tags)
    
    # Public Share metrics
    aggregator.assert_metric('active_directory.dfsr.deleted_files_size', 2097152, tags=public_tags)
    aggregator.assert_metric('active_directory.dfsr.staging_folder_size', 10485760, tags=public_tags)
    aggregator.assert_metric('active_directory.dfsr.file_installs_retried', 25, tags=public_tags)
    aggregator.assert_metric('active_directory.dfsr.conflict_files_size', 1048576, tags=public_tags)

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
    aggregator.assert_metric('active_directory.ds.threads_in_use', 5, count=1)
    
    # Netlogon metrics SHOULD be collected (service is mocked as running)
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 2, count=1)
    
    # DFSR metrics should NOT be collected (service is mocked as not running)
    aggregator.assert_metric('active_directory.dfsr.staging_folder_size', count=0)

@mock.patch('datadog_checks.base.utils.windows_service.is_service_running')
def test_emits_service_checks(mock_is_service_running, aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    """
    Tests that service checks are emitted correctly based on service status.
    """
    mock_performance_objects({})  # No metrics needed for this test

    # Simulate NTDS and Netlogon running, DFSR not running
    def service_side_effect(service_name, log=None):
        if service_name in ['NTDS', 'Netlogon', 'DNS', 'Kdc', 'W32Time', 'ADWS']:
            return True, 4, None  # Running state
        else:
            return False, 1, None  # Stopped state
    mock_is_service_running.side_effect = service_side_effect

    instance_config = [{'host': dd_default_hostname, 'emit_service_status': True}]
    check = ActiveDirectoryCheckV2('active_directory', {}, instance_config)
    dd_run_check(check)

    global_tags = [f'server:{dd_default_hostname}']

    # Assert all service checks
    # Services that are running (mocked as running in service_side_effect)
    aggregator.assert_service_check('active_directory.service.ntds', ServiceCheck.OK, tags=global_tags)
    aggregator.assert_service_check('active_directory.service.dns', ServiceCheck.OK, tags=global_tags)
    aggregator.assert_service_check('active_directory.service.kdc', ServiceCheck.OK, tags=global_tags)
    aggregator.assert_service_check('active_directory.service.netlogon', ServiceCheck.OK, tags=global_tags)
    aggregator.assert_service_check('active_directory.service.w32time', ServiceCheck.OK, tags=global_tags)
    aggregator.assert_service_check('active_directory.service.adws', ServiceCheck.OK, tags=global_tags)
    
    # Service that is stopped (DFSR is not in the running list)
    aggregator.assert_service_check('active_directory.service.dfsr', ServiceCheck.CRITICAL, tags=global_tags)

@mock.patch('datadog_checks.active_directory.check.ActiveDirectoryCheckV2._is_service_running', return_value=True)
def test_all_metrics_comprehensive(mock_is_service_running, aggregator, dd_default_hostname, dd_run_check, mock_performance_objects, core_performance_objects, optional_performance_objects):
    """
    Comprehensive test that ensures ALL metrics defined in metrics.py are properly collected
    when all services are running. This serves as a safety net for any future metric additions.
    """
    # Combine all performance objects
    all_performance_objects = {**core_performance_objects, **optional_performance_objects}
    mock_performance_objects(all_performance_objects)
    
    check = ActiveDirectoryCheckV2('active_directory', {}, [{'host': dd_default_hostname}])
    dd_run_check(check)
    
    global_tags = [f'server:{dd_default_hostname}']
    total_instance_tags = global_tags + ['instance:_Total']
    
    # Assert all NTDS metrics (core metrics, always collected)
    # DRA Inbound metrics
    aggregator.assert_metric('active_directory.dra.inbound.bytes.after_compression', 1000, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.bytes.before_compression', 2000, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.bytes.not_compressed', 3000, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', 6000, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.objects.remaining', 0, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.objects.persec', 10, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.objects.applied_persec', 8, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.objects.filtered_persec', 2, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.objects.remaining_in_packet', 0, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.properties.applied_persec', 50, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.properties.filtered_persec', 5, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.properties.total_persec', 55, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.values.dns_persec', 20, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.inbound.values.total_persec', 30, tags=global_tags)
    
    # DRA Outbound metrics
    aggregator.assert_metric('active_directory.dra.outbound.bytes.after_compression', 500, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.bytes.before_compression', 1000, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.bytes.not_compressed', 2000, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.bytes.total', 3500, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.objects.filtered_persec', 1, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.objects.persec', 5, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.properties.persec', 25, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.values.dns_persec', 10, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.outbound.values.total_persec', 15, tags=global_tags)
    
    # Other NTDS metrics
    aggregator.assert_metric('active_directory.dra.replication.pending_synchronizations', 0, tags=global_tags)
    aggregator.assert_metric('active_directory.dra.sync_requests_made', 100, tags=global_tags)
    aggregator.assert_metric('active_directory.ds.threads_in_use', 5, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.client_sessions', 10, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.bind_time', 50, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.successful_binds_persec', 20, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.searches_persec', 100, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.writes_persec', 15, tags=global_tags)
    aggregator.assert_metric('active_directory.ldap.active_threads', 4, tags=global_tags)
    aggregator.assert_metric('active_directory.ds.client_binds_persec', 25, tags=global_tags)
    
    # Assert all Netlogon metrics
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 2, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_holders', 1, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_acquires', 1000, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_timeouts', 5, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_hold_time', 0.5, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.netlogon.last_authentication_time', 300, tags=total_instance_tags)
    
    # Assert all Security metrics
    aggregator.assert_metric('active_directory.security.ntlm_authentications', 50, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.security.kerberos_authentications', 200, tags=total_instance_tags)
    
    # Assert all DHCP metrics
    aggregator.assert_metric('active_directory.dhcp.binding_updates_dropped', 15, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.dhcp.failover.update_pending_messages', 3, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.dhcp.failover.messages_received', 10.5, tags=total_instance_tags)
    aggregator.assert_metric('active_directory.dhcp.failover.messages_sent', 12.3, tags=total_instance_tags)
    
    # Assert all DFSR metrics for both replication groups
    for group_name, values in [('Domain System Volume', [1048576, 5242880, 10, 524288]), 
                               ('Public Share', [2097152, 10485760, 25, 1048576])]:
        group_tags = global_tags + [f'replication_group:{group_name}']
        aggregator.assert_metric('active_directory.dfsr.deleted_files_size', values[0], tags=group_tags)
        aggregator.assert_metric('active_directory.dfsr.staging_folder_size', values[1], tags=group_tags)
        aggregator.assert_metric('active_directory.dfsr.file_installs_retried', values[2], tags=group_tags)
        aggregator.assert_metric('active_directory.dfsr.conflict_files_size', values[3], tags=group_tags)
    
    # Ensure no metrics were missed
    aggregator.assert_all_metrics_covered()