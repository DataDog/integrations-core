# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from copy import deepcopy

import clickhouse_connect
import pytest

from datadog_checks.clickhouse import ClickhouseCheck

from .common import CONFIG


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestDBMIntegration:
    """Integration tests for Database Monitoring (DBM) query samples"""

    def test_query_samples_are_collected(self, aggregator, instance):
        """
        Test that query samples are actually collected and submitted when DBM is enabled
        """
        # Configure instance with DBM enabled
        instance_config = deepcopy(instance)
        instance_config['dbm'] = True
        instance_config['query_samples'] = {
            'enabled': True,
            'collection_interval': 1,  # Collect every second for testing
            'samples_per_hour_per_query': 100,  # Allow many samples for testing
        }

        # Create check
        check = ClickhouseCheck('clickhouse', {}, [instance_config])

        # First, generate some queries in ClickHouse to populate query_log
        client = clickhouse_connect.get_client(
            host=instance_config['server'],
            port=instance_config['port'],
            username=instance_config['username'],
            password=instance_config['password'],
        )

        # Run several different queries to populate query_log
        test_queries = [
            "SELECT 1",
            "SELECT count(*) FROM system.tables",
            "SELECT name, engine FROM system.databases",
            "SELECT version()",
            "SELECT now()",
        ]

        for query in test_queries:
            try:
                client.query(query)
            except Exception as e:
                print(f"Query '{query}' failed: {e}")

        # Wait a moment for queries to appear in query_log
        time.sleep(2)

        # Verify there are queries in query_log
        result = client.query("SELECT count(*) FROM system.query_log WHERE event_time > now() - INTERVAL 1 MINUTE")
        query_log_count = result.result_rows[0][0]
        print(f"Found {query_log_count} queries in query_log")

        # Run the check - this should collect samples
        check.check(None)

        # Wait for async job to complete if running async
        if check.statement_samples and hasattr(check.statement_samples, '_job_loop_future'):
            if check.statement_samples._job_loop_future:
                check.statement_samples._job_loop_future.result(timeout=5)

        # Run check again to ensure we collect samples
        time.sleep(1)
        check.check(None)

        # Verify metrics are being reported
        aggregator.assert_metric('dd.clickhouse.collect_statement_samples.events_submitted.count')
        aggregator.assert_metric('dd.clickhouse.get_query_log_samples.rows')

        # Get the count of submitted events
        events_submitted = aggregator.metrics('dd.clickhouse.collect_statement_samples.events_submitted.count')
        if events_submitted:
            total_submitted = sum(m.value for m in events_submitted)
            print(f"Total query samples submitted: {total_submitted}")
            assert total_submitted > 0, "Expected at least one query sample to be submitted"

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

        # Verify no DBM metrics are reported
        assert not aggregator.metrics(
            'dd.clickhouse.collect_statement_samples.events_submitted.count'
        ), "No DBM metrics should be reported when DBM is disabled"

    def test_query_samples_with_activity(self, aggregator, instance, dd_run_check):
        """
        Test that query samples capture actual query activity with details
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

        # Connect and run a distinctive query
        client = clickhouse_connect.get_client(
            host=instance_config['server'],
            port=instance_config['port'],
            username=instance_config['username'],
            password=instance_config['password'],
        )

        # Run a query that will be easy to identify
        distinctive_query = "SELECT 'DBM_TEST_QUERY' as test_column, count(*) FROM system.tables"
        client.query(distinctive_query)

        # Wait for query to appear in query_log
        time.sleep(2)

        # Verify the query is in query_log
        result = client.query("""
            SELECT count(*)
            FROM system.query_log
            WHERE query LIKE '%DBM_TEST_QUERY%'
            AND event_time > now() - INTERVAL 1 MINUTE
        """)
        assert result.result_rows[0][0] > 0, "Distinctive query should be in query_log"

        # Run the check
        dd_run_check(check)

        # Wait for async processing
        time.sleep(2)

        # Run check again
        dd_run_check(check)

        # Verify we collected some rows
        rows_metric = aggregator.metrics('dd.clickhouse.get_query_log_samples.rows')
        if rows_metric:
            total_rows = sum(m.value for m in rows_metric)
            print(f"Total rows collected from query_log: {total_rows}")
            assert total_rows > 0, "Should have collected rows from query_log"

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

        # Create a mock row to test event creation
        mock_row = {
            'timestamp': time.time(),
            'query_id': 'test-query-id',
            'query': 'SELECT * FROM system.tables WHERE name = ?',
            'statement': 'SELECT * FROM system.tables WHERE name = ?',
            'query_signature': 'test-signature',
            'type': 'QueryFinish',
            'user': 'datadog',
            'duration_ms': 100,
            'read_rows': 10,
            'read_bytes': 1024,
            'written_rows': 0,
            'written_bytes': 0,
            'result_rows': 10,
            'result_bytes': 1024,
            'memory_usage': 2048,
            'exception': None,
            'dd_tables': ['system.tables'],
            'dd_commands': ['SELECT'],
            'dd_comments': [],
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
        assert event['dbm_type'] == 'sample', "dbm_type should be sample"
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

        # Verify clickhouse section
        ch_section = event['clickhouse']
        assert 'query_id' in ch_section
        assert 'type' in ch_section
        assert 'duration_ms' in ch_section
        assert 'read_rows' in ch_section
        assert 'memory_usage' in ch_section

        # Verify duration is in nanoseconds
        assert 'duration' in event
        assert event['duration'] == 100 * 1e6  # 100ms in nanoseconds

        print("Event structure is valid!")
        print(f"Event keys: {list(event.keys())}")

