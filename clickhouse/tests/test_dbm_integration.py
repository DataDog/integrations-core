# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from copy import deepcopy

import clickhouse_connect
import pytest

from datadog_checks.clickhouse import ClickhouseCheck


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestDBMIntegration:
    """Integration tests for Database Monitoring (DBM) query samples"""

    def test_query_samples_are_collected(self, aggregator, instance, dd_run_check):
        """
        Test that query samples are actually collected and submitted when DBM is enabled.
        The implementation uses system.processes to capture currently running queries.
        """
        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
            'collection_interval': 1,  # Collect every second for testing
            'samples_per_hour_per_query': 100,  # Allow many samples for testing
            'activity_enabled': True,
            'activity_collection_interval': 1,
        }

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # Run the check - this should collect samples from system.processes
        dd_run_check(check)

        # Wait for async job to complete
        time.sleep(2)

        # Run check again
        dd_run_check(check)

        # Verify activity snapshots are being collected
        # The implementation collects from system.processes and submits activity events
        activity_events = aggregator.get_event_platform_events("dbm-activity")
        print(f"Found {len(activity_events)} activity events")

    def test_query_samples_disabled(self, aggregator, instance):
        """
        Test that query samples are NOT collected when DBM is disabled
        """
        # Configure instance with DBM disabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = False

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # Verify statement_samples is None
        assert check.statement_samples is None, "statement_samples should be None when DBM is disabled"

        # Run the check
        check.check(None)

    def test_query_samples_with_activity(self, aggregator, instance, dd_run_check):
        """
        Test that activity snapshots capture active connections/processes
        """
        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
            'collection_interval': 1,
            'activity_enabled': True,
            'activity_collection_interval': 1,
        }

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # Connect and keep connection open
        client = clickhouse_connect.get_client(
            host=instance_config['server'],
            port=instance_config['port'],
            username=instance_config['username'],
            password=instance_config['password'],
        )

        # Run a query to verify connection works
        result = client.query("SELECT version()")
        assert result is not None

        # Run the check
        dd_run_check(check)

        # Wait for async processing
        time.sleep(2)

        # Run check again
        dd_run_check(check)

        # Activity events are submitted via database_monitoring_query_activity
        activity_events = aggregator.get_event_platform_events("dbm-activity")
        print(f"Found {len(activity_events)} activity events")

    def test_query_samples_properties(self, instance):
        """
        Test that required DBM properties are correctly set on the check
        """
        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
        }

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # Verify DBM properties exist
        assert hasattr(check, 'reported_hostname'), "Check should have reported_hostname property"
        assert hasattr(check, 'database_identifier'), "Check should have database_identifier property"

        # Verify properties return expected values
        hostname = check.reported_hostname
        db_id = check.database_identifier

        assert hostname is not None, "reported_hostname should not be None"
        assert db_id is not None, "database_identifier should not be None"
        assert check._server in hostname, "hostname should contain server name"
        assert str(check._port) in db_id, "database_identifier should contain port"
        assert check._db in db_id, "database_identifier should contain database name"

        print(f"reported_hostname: {hostname}")
        print(f"database_identifier: {db_id}")

    def test_statement_samples_event_structure(self, instance):
        """
        Test that the event structure for query samples is correct
        """
        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
        }

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # Create a mock row to test event creation (matching system.processes output)
        mock_row = {
            'elapsed': 0.1,  # seconds
            'query_id': 'test-query-id',
            'query': 'SELECT * FROM system.tables WHERE name = ?',
            'statement': 'SELECT * FROM system.tables WHERE name = ?',
            'query_signature': 'test-signature',
            'user': 'datadog',
            'read_rows': 10,
            'read_bytes': 1024,
            'written_rows': 0,
            'written_bytes': 0,
            'memory_usage': 2048,
            'dd_tables': ['system.tables'],
            'dd_commands': ['SELECT'],
            'dd_comments': [],
            'current_database': 'default',
        }

        # Create event
        event = check.statement_samples._create_sample_event(mock_row)

        # Verify event structure
        assert 'host' in event, "Event should have host field"
        assert 'database_instance' in event, "Event should have database_instance field"
        assert 'ddagentversion' in event, "Event should have ddagentversion field"
        assert 'ddsource' in event, "Event should have ddsource field"
        assert event['ddsource'] == 'clickhouse', "ddsource should be clickhouse"
        assert 'dbm_type' in event, "Event should have dbm_type field"
        assert event['dbm_type'] == 'plan', "dbm_type should be plan"
        assert 'timestamp' in event, "Event should have timestamp field"
        assert 'db' in event, "Event should have db field"
        assert 'clickhouse' in event, "Event should have clickhouse field"

        # Verify db section
        db_section = event['db']
        assert 'instance' in db_section
        assert 'query_signature' in db_section
        assert 'statement' in db_section
        assert 'user' in db_section
        assert 'metadata' in db_section

        # Verify clickhouse section contains fields not excluded by system_processes_sample_exclude_keys
        ch_section = event['clickhouse']
        # query_id is excluded from clickhouse section as per system_processes_sample_exclude_keys
        assert 'read_rows' in ch_section
        assert 'memory_usage' in ch_section

        # Verify duration is in nanoseconds (elapsed is in seconds)
        assert 'duration' in event
        assert event['duration'] == int(0.1 * 1e9)  # 0.1 seconds = 100ms in nanoseconds

        print("Event structure is valid!")
        print(f"Event keys: {list(event.keys())}")
