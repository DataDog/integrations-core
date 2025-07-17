# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.active_directory import ActiveDirectoryCheck
from datadog_checks.base.constants import ServiceCheck


@pytest.fixture
def netlogon_performance_objects():
    """Mock performance objects including Netlogon and Security counters."""
    return {
        'NTDS': (
            [None],
            {
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
                'DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec': [500],
                'DRA Outbound Bytes Compressed (Between Sites, Before Compression)/sec': [1000],
                'DRA Outbound Bytes Not Compressed (Within Site)/sec': [2000],
                'DRA Outbound Bytes Total/sec': [3500],
                'DRA Outbound Objects Filtered/sec': [1],
                'DRA Outbound Objects/sec': [5],
                'DRA Outbound Properties/sec': [25],
                'DRA Outbound Values (DNs only)/sec': [10],
                'DRA Outbound Values Total/sec': [15],
                'DRA Pending Replication Synchronizations': [0],
                'DRA Sync Requests Made': [100],
                'DS Threads in Use': [5],
                'LDAP Client Sessions': [10],
                'LDAP Bind Time': [50],
                'LDAP Successful Binds/sec': [20],
                'LDAP Searches/sec': [100],
            }
        ),
        'Netlogon': (
            ['_Total'],
            {
                'Semaphore Waiters': [2],
                'Semaphore Holders': [1],
                'Semaphore Acquires': [1000],
                'Semaphore Timeouts': [5],
                'Average Semaphore Hold Time': [0.5],
            }
        ),
        'Security System-Wide Statistics': (
            ['_Total'],
            {
                'NTLM Authentications': [50],
                'Kerberos Authentications': [200],
            }
        ),
    }


def test_netlogon_metrics(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects, netlogon_performance_objects):
    """Test that Netlogon metrics are properly collected."""
    mock_performance_objects(netlogon_performance_objects)
    
    check = ActiveDirectoryCheck('active_directory', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)
    
    global_tags = ['server:{}'.format(dd_default_hostname)]
    
    # Verify service check
    aggregator.assert_service_check('active_directory.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)
    
    # Verify Netlogon metrics
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 2, count=1, tags=global_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_holders', 1, count=1, tags=global_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_acquires', 1000, count=1, tags=global_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_timeouts', 5, count=1, tags=global_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_hold_time', 0.5, count=1, tags=global_tags)
    
    # Verify Security metrics
    aggregator.assert_metric('active_directory.security.ntlm_authentications', 50, count=1, tags=global_tags)
    aggregator.assert_metric('active_directory.security.kerberos_authentications', 200, count=1, tags=global_tags)


def test_netlogon_metrics_missing_counters(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    """Test graceful handling when Netlogon counters are not available."""
    # Mock only NTDS counters, no Netlogon
    performance_objects = {
        'NTDS': (
            [None],
            {counter: [9000] for counter in [
                'DRA Inbound Bytes Total/sec',
                'DRA Outbound Bytes Total/sec',
                'DS Threads in Use',
                'LDAP Client Sessions',
                'LDAP Bind Time',
                'LDAP Successful Binds/sec',
                'LDAP Searches/sec',
            ]}
        ),
    }
    mock_performance_objects(performance_objects)
    
    check = ActiveDirectoryCheck('active_directory', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)
    
    global_tags = ['server:{}'.format(dd_default_hostname)]
    
    # Service check should still be OK
    aggregator.assert_service_check('active_directory.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)
    
    # Verify NTDS metrics are still collected
    aggregator.assert_metric('active_directory.dra.inbound.bytes.total', 9000, count=1, tags=global_tags)
    
    # Netlogon metrics should not be present
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', count=0)
    aggregator.assert_metric('active_directory.security.ntlm_authentications', count=0)


def test_netlogon_custom_instance(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    """Test Netlogon metrics with custom instance configuration."""
    performance_objects = {
        'Netlogon': (
            ['DC01', 'DC02'],
            {
                'Semaphore Waiters': [3, 1],
                'Semaphore Holders': [2, 0],
                'Semaphore Acquires': [500, 300],
                'Semaphore Timeouts': [2, 1],
                'Average Semaphore Hold Time': [0.3, 0.1],
            }
        ),
    }
    mock_performance_objects(performance_objects)
    
    # Configure to monitor specific instance
    config = {
        'extra_metrics': {
            'Netlogon': {
                'name': 'netlogon',
                'include': ['DC01'],
                'counters': [
                    {'Semaphore Waiters': 'semaphore_waiters'},
                    {'Semaphore Holders': 'semaphore_holders'},
                ]
            }
        }
    }
    
    check = ActiveDirectoryCheck('active_directory', {}, [{'host': dd_default_hostname, **config}])
    check.hostname = dd_default_hostname
    dd_run_check(check)
    
    global_tags = ['server:{}'.format(dd_default_hostname)]
    instance_tags = global_tags + ['instance:DC01']
    
    # Only DC01 metrics should be collected
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', 3, count=1, tags=instance_tags)
    aggregator.assert_metric('active_directory.netlogon.semaphore_holders', 2, count=1, tags=instance_tags)
    
    # DC02 should not be collected
    dc02_tags = global_tags + ['instance:DC02']
    aggregator.assert_metric('active_directory.netlogon.semaphore_waiters', tags=dc02_tags, count=0)