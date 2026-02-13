# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import queue
import threading
import time
from typing import Dict

import pytest
from psycopg import Connection
from psycopg.errors import AdminShutdown

from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager, PostgresConnectionArgs

from .utils import _get_superconn


def _create_conn_args(pg_instance, application_name="test_connection_pool"):
    """
    Helper function to create PostgresConnectionArgs with common test configuration.

    Args:
        pg_instance: The PostgreSQL instance configuration
        application_name: The application name for the connection

    Returns:
        PostgresConnectionArgs: Configured connection arguments
    """
    return PostgresConnectionArgs(
        application_name=application_name,
        username=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )


def _make_base_args(**overrides):
    """Helper to create base connection arguments with defaults."""
    base = {
        "application_name": "test_app",
        "username": "testuser",
        "password": "testpass",
        "host": "localhost",
        "port": 5432,
        "ssl_mode": "allow",
    }
    base.update(overrides)
    return base


def _make_expected_kwargs(**overrides):
    """Helper to create expected kwargs with defaults."""
    base = {
        "application_name": "test_app",
        "user": "testuser",
        "password": "testpass",
        "host": "localhost",
        "port": 5432,
        "sslmode": "allow",
    }
    base.update(overrides)

    # Remove None values to match actual implementation behavior
    return {k: v for k, v in base.items() if v is not None}


@pytest.mark.parametrize(
    "init_args, dbname, expected",
    [
        # Basic functionality tests
        (_make_base_args(), "testdb", _make_expected_kwargs(dbname="testdb")),
        (_make_base_args(), "override_db", _make_expected_kwargs(dbname="override_db")),
        (_make_base_args(), "overridedb", _make_expected_kwargs(dbname="overridedb")),
        # Optional parameter exclusion tests
        (_make_base_args(password=None), "testdb", _make_expected_kwargs(dbname="testdb", password=None)),
        (_make_base_args(port=None), "testdb", _make_expected_kwargs(dbname="testdb", port=None)),
        (
            _make_base_args(password=""),
            "testdb",
            _make_expected_kwargs(dbname="testdb", password=None),  # Empty string excluded
        ),
        # SSL configuration tests
        (
            _make_base_args(
                ssl_mode="require",
                ssl_cert="/path/to/client.crt",
                ssl_key="/path/to/client.key",
                ssl_root_cert="/path/to/ca.crt",
                ssl_password="sslkeypass",
            ),
            "ssldb",
            _make_expected_kwargs(
                dbname="ssldb",
                sslmode="require",
                sslcert="/path/to/client.crt",
                sslkey="/path/to/client.key",
                sslrootcert="/path/to/ca.crt",
                sslpassword="sslkeypass",
            ),
        ),
        (
            _make_base_args(ssl_mode="prefer", ssl_cert="/path/to/client.crt", ssl_key="/path/to/client.key"),
            "override_ssl_db",
            _make_expected_kwargs(
                dbname="override_ssl_db", sslmode="prefer", sslcert="/path/to/client.crt", sslkey="/path/to/client.key"
            ),
        ),
        (
            _make_base_args(ssl_mode="verify-full"),
            "testdb",
            _make_expected_kwargs(dbname="testdb", sslmode="verify-full"),
        ),
        # SSL parameter exclusion tests
        (
            _make_base_args(ssl_mode="require", ssl_cert=None, ssl_key=None, ssl_root_cert=None, ssl_password=None),
            "testdb",
            _make_expected_kwargs(dbname="testdb", sslmode="require"),
        ),
        (
            _make_base_args(
                ssl_mode="require",
                ssl_cert="/path/to/client.crt",
                ssl_key=None,
                ssl_root_cert="/path/to/ca.crt",
                ssl_password=None,
            ),
            "testdb",
            _make_expected_kwargs(
                dbname="testdb", sslmode="require", sslcert="/path/to/client.crt", sslrootcert="/path/to/ca.crt"
            ),
        ),
        # Edge cases
        (
            _make_base_args(password="", ssl_mode=""),
            "testdb",
            _make_expected_kwargs(
                dbname="testdb",
                password=None,  # Empty string excluded
                sslmode="",
            ),
        ),
        (
            _make_base_args(),
            "",  # Empty string dbname
            _make_expected_kwargs(dbname=""),  # Empty string is valid
        ),
        # Socket connection tests (no host or password)
        (
            _make_base_args(host=None, password=None),
            "testdb",
            _make_expected_kwargs(dbname="testdb", host=None, password=None),
        ),
        (
            _make_base_args(host=None, password=None, port=None),
            "testdb",
            _make_expected_kwargs(dbname="testdb", host=None, password=None, port=None),
        ),
        (
            _make_base_args(host="", password=""),
            "testdb",
            _make_expected_kwargs(dbname="testdb", host=None, password=None),  # Empty strings excluded
        ),
    ],
)
def test_postgres_connection_args_as_kwargs(init_args, dbname, expected):
    """
    Validates that PostgresConnectionArgs.as_kwargs() correctly outputs connection kwargs
    under various combinations of initialization parameters and dbname.

    Test cases cover:
    - Basic connection parameters (user, password, host, port)
    - SSL configuration (ssl_mode, ssl_cert, ssl_key, ssl_root_cert, ssl_password)
    - Edge cases (None values, empty strings, missing optional parameters)
    - dbname parameter handling
    - Parameter exclusion when values are None
    """
    args = PostgresConnectionArgs(**init_args)
    kwargs = args.as_kwargs(dbname=dbname)

    assert kwargs == expected


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_basic_connection(pg_instance: Dict[str, str]):
    """
    Test basic connection acquisition, query execution, and pool stats
    for a single dbname using LRUConnectionPoolManager.
    """
    conn_args = _create_conn_args(pg_instance, "test_basic_connection")
    manager = LRUConnectionPoolManager(max_db=3, base_conn_args=conn_args, pool_config={"min_size": 1, "max_size": 2})

    try:
        dbname = pg_instance["dbname"]
        with manager.get_connection(dbname) as conn:
            assert isinstance(conn, Connection)

            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result == (1,)

        stats = manager.get_pool_stats(dbname)
        assert stats is not None
        # Basic presence checks
        assert "last_used" in stats
        assert isinstance(stats["last_used"], float)

        # Pool state
        assert stats["pool_min"] == 0
        assert stats["pool_max"] == 2
        assert 1 <= stats["pool_size"] <= 2
        assert stats["pool_available"] >= 1  # Should be 1 or 2 after release

        # Usage metrics
        assert stats["connections_num"] >= 1
        assert stats["requests_num"] == 1
        assert stats["requests_waiting"] == 0

    finally:
        manager.close_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_lru_eviction_and_connection_rotation(pg_instance):
    """
    Opens and closes multiple connections across dogs_n databases and asserts LRU behavior
    and correct enforcement of min_size=0, max_size=2 per pool.
    """
    conn_args = _create_conn_args(pg_instance, "test_lru_eviction_and_connection_rotation")
    manager = LRUConnectionPoolManager(max_db=3, base_conn_args=conn_args)

    dbnames = [f"dogs_{i}" for i in range(5)]  # 5 dbs, max pool limit is 3

    # Open a connection to each dbname once
    for dbname in dbnames:
        with manager.get_connection(dbname) as conn:
            assert isinstance(conn, Connection)
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result == (1,)

    # After connecting to 5 DBs, only 3 should remain in the pool
    assert len(manager.pools) == 3

    # Check that those pools respect pool_config limits
    for _dbname, (pool, _last_used, persistent) in manager.pools.items():
        stats = pool.get_stats()
        assert stats["pool_min"] == 0
        assert stats["pool_max"] == 2
        assert stats["pool_size"] <= 2
        assert persistent is False

    manager.close_all()
    # After closing, pool dict should be empty
    assert len(manager.pools) == 0


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_lru_eviction_order(pg_instance):
    """
    Verifies that the least recently used dbname pool is evicted when the max_db limit is exceeded.
    """
    conn_args = _create_conn_args(pg_instance, "test_lru_eviction_order")
    manager = LRUConnectionPoolManager(max_db=3, base_conn_args=conn_args)

    try:
        # Step 1–3: Fill up with 3 distinct pools
        for db in ["dogs_0", "dogs_1", "dogs_2"]:
            with manager.get_connection(db) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")

        # Access dogs_0 again to make it most recently used
        with manager.get_connection("dogs_0") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # Step 4: Add a new pool — this should evict dogs_1 (oldest)
        with manager.get_connection("dogs_3") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        # Step 5: Verify eviction
        current_pools = list(manager.pools.keys())
        assert "dogs_1" not in current_pools
        assert set(current_pools) == {"dogs_0", "dogs_2", "dogs_3"}

    finally:
        manager.close_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_max_idle_closes_and_reopens_connection(pg_instance):
    """
    Tests that a connection is closed after max_idle seconds of idleness,
    and that the pool reopens a usable connection on next use.
    """
    conn_args = _create_conn_args(pg_instance, "test_max_idle_closes_and_reopens_connection")

    manager = LRUConnectionPoolManager(
        max_db=1,
        base_conn_args=conn_args,
        pool_config={
            "max_idle": 0.5,  # second timeout
        },
    )

    dbname = pg_instance["dbname"]

    try:
        # Step 1: Open a connection and return it
        with manager.get_connection(dbname) as conn:
            assert isinstance(conn, Connection)
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        stats1 = manager.get_pool_stats(dbname)
        first_conn_count = stats1["connections_num"]
        assert first_conn_count == 1
        assert stats1["pool_available"] == 1

        # Step 2: Wait longer than max_idle so idle conn is closed
        time.sleep(2)

        # Step 3: Re-acquire a connection
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        stats2 = manager.get_pool_stats(dbname)
        assert stats2["connections_num"] >= 2, "Expected a new connection to be opened after idle timeout"
        assert stats2["pool_size"] <= 1

    finally:
        manager.close_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_statement_timeout_configuration(pg_instance: Dict[str, str]):
    """
    Test that statement_timeout is properly configured on connections and that
    timeout behavior works correctly.
    """
    conn_args = _create_conn_args(pg_instance, "test_statement_timeout")

    manager = LRUConnectionPoolManager(
        max_db=1,
        base_conn_args=conn_args,
        statement_timeout=1000,  # 1 second
    )

    try:
        dbname = pg_instance["dbname"]
        with manager.get_connection(dbname) as conn:
            assert isinstance(conn, Connection)

            with conn.cursor() as cur:
                # Verify timeout is set correctly
                cur.execute("SHOW statement_timeout")
                timeout = cur.fetchone()[0]
                assert timeout == "1s"

                # Test that a normal query works
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result == (1,)

        # Test timeout behavior with a long query
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                # This should timeout after 1 second
                with pytest.raises(Exception) as exc_info:
                    cur.execute("SELECT pg_sleep(2)")

                # Verify it's a timeout-related exception
                error_msg = str(exc_info.value).lower()
                assert any(keyword in error_msg for keyword in ["timeout", "statement_timeout", "canceling"])

    finally:
        manager.close_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_connection_termination_and_recovery(pg_instance):
    """
    Simulates a server-side termination of a connection and verifies the pool
    replaces it and continues working.
    """
    conn_args = _create_conn_args(pg_instance, "test_connection_termination_and_recovery")

    manager = LRUConnectionPoolManager(
        max_db=1,
        base_conn_args=conn_args,
        pool_config={
            "min_size": 0,
            "max_size": 1,
            "max_idle": 60,
            "open": True,
        },
    )

    dbname = pg_instance["dbname"]

    try:
        # Open a connection and get its PID
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_backend_pid()")
                pid = cur.fetchone()[0]
                print(f"Target connection PID: {pid}")

        # Terminate the connection from superuser
        with _get_superconn(pg_instance) as superconn:
            with superconn.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
                result = cur.fetchone()[0]
                assert result is True, "pg_terminate_backend() failed"

        # Try using the connection again
        try:
            with manager.get_connection(dbname) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 42")
                    assert cur.fetchone()[0] == 42
        except AdminShutdown:
            # Connection was terminated, psycopg3 will not retry and raise an AdminShutdown error
            # But we should still be able to successfully open a new connection next attempt
            # This should be caught and handled by the application using the connection
            with manager.get_connection(dbname) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 42")
                    assert cur.fetchone()[0] == 42

        stats = manager.get_pool_stats(dbname)
        assert stats["connections_num"] >= 2, "Expected connection to be reopened after termination"

    finally:
        manager.close_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_persistent_pool_eviction_behavior(pg_instance):
    """
    Ensures persistent pools are not evicted while non-persistent ones are available.
    """
    conn_args = _create_conn_args(pg_instance, "test_persistent_pool_eviction_behavior")

    manager = LRUConnectionPoolManager(max_db=3, base_conn_args=conn_args)

    try:
        # Fill pool with 3 connections
        dbs = ["dogs_0", "dogs_1", "dogs_2"]
        with manager.get_connection(dbs[0]):  # non-persistent
            pass
        with manager.get_connection(dbs[1]):  # non-persistent
            pass
        with manager.get_connection(dbs[2], persistent=True):  # persistent
            pass

        # Trigger eviction by adding one more
        with manager.get_connection("dogs_3"):
            pass

        pool_keys = list(manager.pools.keys())

        # Assert persistent pool still exists
        assert "dogs_2" in pool_keys

        # One of the non-persistent dbs must be evicted
        evicted = set(dbs[:2]) - set(pool_keys)
        assert len(evicted) == 1, "One non-persistent db should have been evicted"

        # Final pool should contain 3 entries
        assert len(pool_keys) == 3

    finally:
        manager.close_all()
        assert len(manager.pools) == 0


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_eviction_when_all_pools_are_persistent(pg_instance):
    """
    Ensures that if all existing pools are persistent, the least recently used one
    is still evicted to make room for a new pool.
    """
    conn_args = _create_conn_args(pg_instance, "test_eviction_when_all_pools_are_persistent")

    manager = LRUConnectionPoolManager(max_db=3, base_conn_args=conn_args)

    try:
        # Open 3 persistent pools
        dbs = ["dogs_0", "dogs_1", "dogs_2"]
        for db in dbs:
            with manager.get_connection(db, persistent=True):
                pass

        # Re-access dogs_1 to update its recency
        with manager.get_connection("dogs_1"):
            pass

        # dogs_0 is now the least recently used persistent pool

        # Open a new pool to trigger eviction
        with manager.get_connection("dogs_3", persistent=True):
            pass

        current_pools = list(manager.pools.keys())

        # Should have evicted dogs_0
        assert "dogs_0" not in current_pools, "Expected least recently used persistent pool to be evicted"
        assert "dogs_1" in current_pools
        assert "dogs_2" in current_pools
        assert "dogs_3" in current_pools
        assert len(current_pools) == 3

    finally:
        manager.close_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_connection_proxy_exception_handling(pg_instance: Dict[str, str]):
    """
    Test that ConnectionProxy properly handles exceptions and releases connections.
    """
    conn_args = _create_conn_args(pg_instance, "test_proxy_exceptions")

    manager = LRUConnectionPoolManager(max_db=1, base_conn_args=conn_args)

    try:
        dbname = pg_instance["dbname"]

        # Test normal usage first
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result == (1,)

        # Test exception handling - this should raise an exception
        with pytest.raises(Exception) as exc_info:
            with manager.get_connection(dbname) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM nonexistent_table")

        # Verify it's a database-related exception
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["relation", "table", "nonexistent", "does not exist"])

        # Verify connection is still available after exception
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result == (1,)

        # Test that pool stats are still valid after exception
        stats = manager.get_pool_stats(dbname)
        assert stats is not None
        assert stats["pool_available"] == 1

    finally:
        manager.close_all()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_concurrent_access_and_thread_safety(pg_instance: Dict[str, str]):
    """
    Test that the pool manager handles concurrent access safely from multiple threads.
    """
    conn_args = _create_conn_args(pg_instance, "test_concurrent")

    manager = LRUConnectionPoolManager(max_db=2, base_conn_args=conn_args)
    results = queue.Queue()

    def worker(dbname):
        """Worker function that accesses a database and reports results."""
        try:
            with manager.get_connection(dbname) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_sleep(0.2), 1")  # simulate work
                    result = cur.fetchone()
                    if result[-1] == 1:
                        results.put(f"success_{dbname}")
                    else:
                        results.put(f"error_{dbname}: unexpected result {result}")
        except Exception as e:
            results.put(f"error_{dbname}: {e}")

    try:
        # Start multiple threads accessing different databases
        threads = []
        for i in range(10):
            dbname = f"dogs_{i % 2}"  # Only 2 unique dbs, 10 threads, to test connection contention
            thread = threading.Thread(target=worker, args=(dbname,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        success_count = 0
        error_count = 0
        while not results.empty():
            result = results.get()
            if result.startswith("success_"):
                success_count += 1
            else:
                error_count += 1
                print(f"Thread error: {result}")

        assert success_count == 10, (
            f"Expected all 10 operations to succeed, got {success_count} successes and {error_count} errors"
        )

        # Verify pool limits are respected
        assert len(manager.pools) <= 5, f"Expected max 5 pools, got {len(manager.pools)}"

        # Verify all pools are functional after concurrent access
        for dbname in list(manager.pools.keys()):
            stats = manager.get_pool_stats(dbname)
            assert stats is not None, f"Pool stats should be available for {dbname}"
            assert stats["pool_available"] == 2, f"Pool should have available connections for {dbname}"
            assert stats["pool_size"] == 2, f"Pool should have size 2 for {dbname}"

    finally:
        manager.close_all()
        assert len(manager.pools) == 0, "All pools should be closed"


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_commenter_cursor_functionality(pg_instance: Dict[str, str]):
    """
    Test that CommenterCursor properly prepends SQL comments and handles ignore_query_metric parameter
    when used with LRUConnectionPoolManager.
    """
    conn_args = _create_conn_args(pg_instance, "test_commenter_cursor")
    manager = LRUConnectionPoolManager(max_db=1, base_conn_args=conn_args, pool_config={"min_size": 1, "max_size": 1})

    try:
        dbname = pg_instance["dbname"]

        # Test normal query execution with CommenterCursor
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT generate_series(1, 5) AS number")
                result = cur.fetchall()
                assert len(result) == 5
                assert all(isinstance(row[0], int) for row in result)

        # Verify SQL comment is prepended
        _verify_sql_comment_prepended(pg_instance, "generate_series", False)

        # Test query with ignore_query_metric=True
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT generate_series(1, 3) AS number", ignore_query_metric=True)
                result = cur.fetchall()
                assert len(result) == 3
                assert all(isinstance(row[0], int) for row in result)

        # Verify SQL comment with DDIGNORE is prepended
        _verify_sql_comment_prepended(pg_instance, "generate_series", True)

        # Test multiple queries to ensure CommenterCursor works consistently
        with manager.get_connection(dbname) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database()")
                result = cur.fetchone()
                assert result[0] == dbname

        _verify_sql_comment_prepended(pg_instance, "current_database", False)

    finally:
        manager.close_all()


def _verify_sql_comment_prepended(pg_instance, query_pattern, ignore_query_metric):
    """
    Verify that SQL comments are properly prepended to queries in pg_stat_activity.
    """
    super_conn = _get_superconn(pg_instance)
    try:
        with super_conn.cursor() as cursor:
            cursor.execute(
                (
                    "SELECT query FROM pg_stat_activity WHERE query LIKE %s "
                    "AND query NOT LIKE '%%pg_stat_activity%%' "
                    "ORDER BY query_start DESC LIMIT 1"
                ),
                (f"%{query_pattern}%",),
            )
            result = cursor.fetchall()
            assert len(result) > 0, f"No queries found matching pattern '{query_pattern}'"

            query_text = result[0][0]
            # Decode bytes to string if necessary
            if isinstance(query_text, bytes):
                query_text = query_text.decode('utf-8')

            expected_comment = "/* service='datadog-agent' */"

            if ignore_query_metric:
                expected_comment = f"/* DDIGNORE */ {expected_comment}"

            assert query_text.startswith(expected_comment), (
                f"Query should start with '{expected_comment}', but got: {query_text[:100]}..."
            )
    finally:
        super_conn.close()


def test_closed_state_and_pool_creation_prevention():
    """
    Test that the pool manager correctly tracks closed state and prevents new pool creation after closing.

    This test verifies:
    1. The is_closed() method returns the correct state
    2. New pools cannot be created after close_all() is called
    3. New connections cannot be created after close_all() is called
    """
    # Create a pool manager with mock connection args (no real DB needed for this test)
    conn_args = PostgresConnectionArgs(
        application_name="test_closed_state",
        username="testuser",
        password="testpass",
        host="localhost",
        port=5432,
    )

    manager = LRUConnectionPoolManager(max_db=2, base_conn_args=conn_args)

    # Initially should not be closed
    assert not manager.is_closed()

    # Close the manager
    manager.close_all()

    # Should now be closed
    assert manager.is_closed()

    # Attempting to get a connection should raise RuntimeError
    with pytest.raises(RuntimeError, match="Pool manager is closed and cannot get connection"):
        manager.get_connection("testdb")

    # Calling close_all() again should not cause issues (idempotent)
    manager.close_all()
    assert manager.is_closed()

    # Still should not be able to create new connections
    with pytest.raises(RuntimeError, match="Pool manager is closed and cannot get connection"):
        manager.get_connection("testdb")
