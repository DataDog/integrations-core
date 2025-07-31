# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from typing import Dict

from psycopg import Connection
from psycopg.errors import AdminShutdown

import pytest

from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager, PostgresConnectionArgs
from .utils import _get_superconn

@pytest.mark.parametrize(
    "init_args, override_dbname, expected",
    [
        # Case 1: Full initialization, no override
        (
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "alice",
                "password": "secret",
                "host": "localhost",
                "port": 5432,
                "dbname": "mydb"
            },
            None,
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "alice",
                "password": "secret",
                "host": "localhost",
                "port": 5432,
                "dbname": "mydb",
                "sslmode": "allow"
            }
        ),
        # Case 2: No dbname in init, dbname provided via override
        (
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "bob",
                "password": "pw123",
                "host": "127.0.0.1",
                "port": 5433,
                "dbname": None
            },
            "override_db",
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "bob",
                "password": "pw123",
                "host": "127.0.0.1",
                "port": 5433,
                "dbname": "override_db",
                "sslmode": "allow"
            }
        ),
        # Case 3: dbname in init, overridden at call time
        (
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "carol",
                "password": "pass",
                "host": "db.internal",
                "port": 5432,
                "dbname": "initdb"
            },
            "overridedb",
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "carol",
                "password": "pass",
                "host": "db.internal",
                "port": 5432,
                "dbname": "overridedb",
                "sslmode": "allow"
            }
        ),
        # Case 4: No dbname anywhere
        (
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "dave",
                "password": "1234",
                "host": "localhost",
                "port": 5432,
                "dbname": None,
            },
            None,
            {
                "application_name": "test_postgres_connection_args_as_kwargs",
                "user": "dave",
                "password": "1234",
                "host": "localhost",
                "port": 5432,
                "dbname": None,
                "sslmode": "allow"
            }
        ),
    ]
)
def test_postgres_connection_args_as_kwargs(init_args, override_dbname, expected):
    """
    Validates that PostgresConnectionArgs.as_kwargs() correctly outputs connection kwargs
    under various combinations of dbname initialization and override.
    """
    args = PostgresConnectionArgs(**init_args)
    kwargs = args.as_kwargs(dbname=override_dbname)

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

    manager = LRUConnectionPoolManager(
        max_db=3,
        base_conn_args=conn_args,
        pool_config={"min_size": 1, "max_size": 2}
    )

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

    manager = LRUConnectionPoolManager(
        max_db=3,
        base_conn_args=base_conn_args
    )

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
    for dbname, (pool, last_used) in manager.pools.items():
        stats = pool.get_stats()
        assert stats["pool_min"] == 0
        assert stats["pool_max"] == 1
        assert stats["pool_size"] <= 1

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
        }
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
        }
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
