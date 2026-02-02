# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""Tests for read-only enforcement of custom_queries."""
import psycopg
import pytest

from .common import DB_NAME, HOST, PASSWORD, PORT, USER


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_query_write_operations_blocked(dd_run_check, pg_instance, integration_check):
    """Verify custom queries cannot perform write operations."""

    # Setup: Create test table with data
    conn = psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD, port=PORT)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            cursor.execute("CREATE TABLE test_readonly_table (id INT PRIMARY KEY, value VARCHAR(50))")
            cursor.execute("INSERT INTO test_readonly_table VALUES (1, 'original')")
            conn.commit()

        # Configure instance with custom_query that attempts INSERT
        pg_instance['custom_queries'] = [
            {
                'query': "INSERT INTO test_readonly_table VALUES (999, 'should_fail')",
                'columns': [{'name': 'result', 'type': 'gauge'}]
            }
        ]

        # Execute check - should raise exception due to read-only enforcement
        check = integration_check(pg_instance)

        # The check should complete but log an error for the failed query
        # We don't expect a full check failure, just the custom query to fail
        dd_run_check(check)

        # Verify: No data was written
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM test_readonly_table WHERE id = 999")
            count = cursor.fetchone()[0]
            assert count == 0, "Write operation should have been blocked by read-only mode"

            # Verify original data is intact
            cursor.execute("SELECT COUNT(*) FROM test_readonly_table")
            total_count = cursor.fetchone()[0]
            assert total_count == 1, "Original data should be intact"

    finally:
        # Cleanup
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            conn.commit()
        conn.close()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_query_update_operations_blocked(dd_run_check, pg_instance, integration_check):
    """Verify custom queries cannot perform UPDATE operations."""

    # Setup: Create test table with data
    conn = psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD, port=PORT)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            cursor.execute("CREATE TABLE test_readonly_table (id INT PRIMARY KEY, value VARCHAR(50))")
            cursor.execute("INSERT INTO test_readonly_table VALUES (1, 'original')")
            conn.commit()

        # Configure instance with custom_query that attempts UPDATE
        pg_instance['custom_queries'] = [
            {
                'query': "UPDATE test_readonly_table SET value = 'modified' WHERE id = 1",
                'columns': [{'name': 'result', 'type': 'gauge'}]
            }
        ]

        # Execute check
        check = integration_check(pg_instance)
        dd_run_check(check)

        # Verify: Data was NOT modified
        with conn.cursor() as cursor:
            cursor.execute("SELECT value FROM test_readonly_table WHERE id = 1")
            value = cursor.fetchone()[0]
            assert value == 'original', "UPDATE operation should have been blocked by read-only mode"

    finally:
        # Cleanup
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            conn.commit()
        conn.close()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_query_delete_operations_blocked(dd_run_check, pg_instance, integration_check):
    """Verify custom queries cannot perform DELETE operations."""

    # Setup: Create test table with data
    conn = psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD, port=PORT)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            cursor.execute("CREATE TABLE test_readonly_table (id INT PRIMARY KEY, value VARCHAR(50))")
            cursor.execute("INSERT INTO test_readonly_table VALUES (1, 'data1'), (2, 'data2')")
            conn.commit()

        # Configure instance with custom_query that attempts DELETE
        pg_instance['custom_queries'] = [
            {
                'query': "DELETE FROM test_readonly_table WHERE id = 1",
                'columns': [{'name': 'result', 'type': 'gauge'}]
            }
        ]

        # Execute check
        check = integration_check(pg_instance)
        dd_run_check(check)

        # Verify: No data was deleted
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM test_readonly_table")
            count = cursor.fetchone()[0]
            assert count == 2, "DELETE operation should have been blocked by read-only mode"

    finally:
        # Cleanup
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            conn.commit()
        conn.close()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_query_read_operations_work(dd_run_check, pg_instance, integration_check, aggregator):
    """Verify custom queries can still perform read operations."""

    # Setup: Create test table with data
    conn = psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD, port=PORT)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            cursor.execute("CREATE TABLE test_readonly_table (id INT PRIMARY KEY, value INT)")
            cursor.execute("INSERT INTO test_readonly_table VALUES (1, 100), (2, 200), (3, 300)")
            conn.commit()

        # Configure instance with custom_query that performs SELECT
        pg_instance['custom_queries'] = [
            {
                'metric_prefix': 'postgresql.test',
                'query': 'SELECT SUM(value) as total FROM test_readonly_table',
                'columns': [{'name': 'total', 'type': 'gauge'}],
                'tags': ['test:readonly']
            }
        ]

        # Execute check - should succeed
        check = integration_check(pg_instance)
        dd_run_check(check)

        # Verify: Metric was collected
        aggregator.assert_metric('postgresql.test.total', value=600, tags=['test:readonly'], count=1, at_least=1)

    finally:
        # Cleanup
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_readonly_table")
            conn.commit()
        conn.close()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_query_create_table_blocked(dd_run_check, pg_instance, integration_check):
    """Verify custom queries cannot perform CREATE TABLE operations."""

    conn = psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD, port=PORT)
    try:
        # Ensure table doesn't exist
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_should_not_exist")
            conn.commit()

        # Configure instance with custom_query that attempts CREATE TABLE
        pg_instance['custom_queries'] = [
            {
                'query': "CREATE TABLE test_should_not_exist (id INT)",
                'columns': [{'name': 'result', 'type': 'gauge'}]
            }
        ]

        # Execute check
        check = integration_check(pg_instance)
        dd_run_check(check)

        # Verify: Table was NOT created
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'test_should_not_exist'
                )
            """)
            exists = cursor.fetchone()[0]
            assert not exists, "CREATE TABLE operation should have been blocked by read-only mode"

    finally:
        # Cleanup (in case test failed)
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_should_not_exist")
            conn.commit()
        conn.close()
