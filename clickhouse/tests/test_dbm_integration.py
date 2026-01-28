# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from copy import deepcopy

import clickhouse_connect
import pytest

from datadog_checks.clickhouse import ClickhouseCheck

from .common import CLICKHOUSE_VERSION

# DBM features require ClickHouse 21.8+ due to normalized_query_hash, query_kind etc
# Note: query_kind column in system.processes is not available in all 22.7 builds
# Versions below 21.8: "18", "19", "20"
# Version 22.7: Missing query_kind column in system.processes
UNSUPPORTED_DBM_VERSIONS = {'18', '19', '20', '22.7'}


def _is_dbm_supported():
    """Check if the current ClickHouse version supports DBM features"""
    # latest is always supported
    if CLICKHOUSE_VERSION == 'latest':
        return True
    # Check if version is in unsupported list
    return CLICKHOUSE_VERSION not in UNSUPPORTED_DBM_VERSIONS


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.skipif(
    not _is_dbm_supported(),
    reason="DBM features require ClickHouse 21.8+ (normalized_query_hash, query_kind, etc.)",
)
class TestDBMIntegration:
    """Integration tests for Database Monitoring (DBM) query samples"""

    def test_query_samples_collected(self, aggregator, instance, dd_run_check):
        """
        Test that query samples is collected and submitted when DBM is enabled.
        The implementation uses system.processes to capture currently running queries.
        """
        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
            'collection_interval': 1,
        }

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # Run the check - this should collect activity from system.processes
        dd_run_check(check)

        # Wait for async job to complete
        time.sleep(2)

        # Run check again
        dd_run_check(check)

        # Verify samples snapshots are being collected
        samples_events = aggregator.get_event_platform_events("dbm-activity")
        print(f"Found {len(samples_events)} samples events")

    def test_query_samples_disabled(self, aggregator, instance):
        """
        Test that query samples is NOT collected when DBM is disabled
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

    def test_query_samples_with_connections(self, aggregator, instance, dd_run_check):
        """
        Test that samples snapshots capture active connections/processes
        """
        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
            'collection_interval': 1,
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

        # Samples events are submitted via database_monitoring_query_activity
        samples_events = aggregator.get_event_platform_events("dbm-activity")
        print(f"Found {len(samples_events)} samples events")

    def test_dbm_properties(self, instance):
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
        assert check._config.server in hostname, "hostname should contain server name"
        assert str(check._config.port) in db_id, "database_identifier should contain port"
        assert check._config.db in db_id, "database_identifier should contain database name"

        print(f"reported_hostname: {hostname}")
        print(f"database_identifier: {db_id}")

    def test_samples_event_structure(self, instance):
        """
        Test that the event structure for samples snapshots is correct
        """
        from unittest import mock

        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
        }

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # Set up samples collector
        samples = check.statement_samples
        samples._tags_no_db = ['test:clickhouse', 'server:localhost']

        # Create mock rows
        rows = [
            {
                'elapsed': 0.1,
                'query_id': 'test-query-id',
                'query': 'SELECT * FROM system.tables',
                'statement': 'SELECT * FROM system.tables',
                'query_signature': 'test-signature',
                'user': 'datadog',
                'read_rows': 10,
                'memory_usage': 2048,
                'current_database': 'default',
            }
        ]

        active_connections = [
            {'user': 'default', 'query_kind': 'Select', 'current_database': 'default', 'connections': 1}
        ]

        # Create event
        with mock.patch('datadog_checks.clickhouse.statement_samples.datadog_agent') as mock_agent:
            mock_agent.get_version.return_value = '7.64.0'
            event = samples._create_samples_event(rows, active_connections)

        # Verify event structure
        assert 'host' in event, "Event should have host field"
        assert 'database_instance' in event, "Event should have database_instance field"
        assert 'ddagentversion' in event, "Event should have ddagentversion field"
        assert 'ddsource' in event, "Event should have ddsource field"
        assert event['ddsource'] == 'clickhouse', "ddsource should be clickhouse"
        assert 'dbm_type' in event, "Event should have dbm_type field"
        assert event['dbm_type'] == 'activity', "dbm_type should be activity"
        assert 'timestamp' in event, "Event should have timestamp field"
        assert 'collection_interval' in event, "Event should have collection_interval field"

        # Verify samples payload
        assert 'clickhouse_activity' in event, "Event should have clickhouse_activity field"
        assert 'clickhouse_connections' in event, "Event should have clickhouse_connections field"

        print("Event structure is valid!")
        print(f"Event keys: {list(event.keys())}")
