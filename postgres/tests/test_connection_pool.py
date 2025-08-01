# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from typing import Dict

import pytest
from psycopg import Connection
from psycopg.errors import AdminShutdown

from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager, PostgresConnectionArgs

from .utils import _get_superconn


def _make_base_args(**overrides):
    """Helper to create base connection arguments with defaults."""
    base = {
        "application_name": "test_app",
        "user": "testuser",
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
    conn_args = PostgresConnectionArgs(
        application_name="test_basic_connection",
        user=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )

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
        assert stats["pool_max"] == 1
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
    and correct enforcement of min_size=0, max_size=1 per pool.
    """
    base_conn_args = PostgresConnectionArgs(
        application_name="test_lru_eviction_and_connection_rotation",
        user=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )

    manager = LRUConnectionPoolManager(max_db=3, base_conn_args=base_conn_args)

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
        assert stats["pool_max"] == 1
        assert stats["pool_size"] <= 1
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
    conn_args = PostgresConnectionArgs(
        application_name="test_lru_eviction_order",
        user=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )

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
    conn_args = PostgresConnectionArgs(
        application_name="test_max_idle_closes_and_reopens_connection",
        user=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )

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
def test_connection_termination_and_recovery(pg_instance):
    """
    Simulates a server-side termination of a connection and verifies the pool
    replaces it and continues working.
    """
    conn_args = PostgresConnectionArgs(
        application_name="test_connection_termination_and_recovery",
        user=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )

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
    conn_args = PostgresConnectionArgs(
        application_name="test_persistent_pool_eviction_behavior",
        user=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )

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
    conn_args = PostgresConnectionArgs(
        application_name="test_eviction_when_all_pools_are_persistent",
        user=pg_instance["username"],
        password=pg_instance["password"],
        host=pg_instance["host"],
        port=int(pg_instance["port"]),
    )

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
