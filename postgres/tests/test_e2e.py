# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import socket

import pytest

from .common import _get_expected_tags, check_bgw_metrics, check_common_metrics
from .utils import _get_conn, _get_superconn


@pytest.mark.e2e
def test_e2e(check, dd_agent_check, pg_instance):
    aggregator = dd_agent_check(pg_instance, rate=True)

    conn = _get_conn(pg_instance)
    conn.execute("SET client_encoding TO 'UTF8'")
    with conn.cursor() as cur:
        cur.execute("SHOW server_version;")
        check.raw_version = cur.fetchone()[0]

        cur.execute("SELECT system_identifier FROM pg_control_system();")
        check.system_identifier = cur.fetchone()[0]

        cur.execute("SHOW cluster_name;")
        check.cluster_name = cur.fetchone()[0]

    check._database_hostname = socket.gethostname().lower()
    check._database_identifier = socket.gethostname().lower()
    check._agent_hostname = socket.gethostname().lower()
    expected_tags = _get_expected_tags(check, pg_instance, with_host=False)
    check_bgw_metrics(aggregator, expected_tags)
    check_common_metrics(aggregator, expected_tags=expected_tags, count=None)


@pytest.mark.e2e
def test_custom_queries_readonly_blocks_writes(dd_agent_check, pg_instance):
    """Verify that all write operations are blocked by read-only enforcement"""
    conn = _get_superconn(pg_instance)

    # Setup: Create test table with full permissions for datadog user
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE public.test_readonly_table (id INT, value TEXT)")
        cur.execute("INSERT INTO public.test_readonly_table VALUES (1, 'initial')")
        cur.execute(f"GRANT ALL ON public.test_readonly_table TO {pg_instance['username']}")
        cur.execute(f"GRANT CREATE ON SCHEMA public TO {pg_instance['username']}")
        conn.commit()

    try:
        # Test each type of write operation
        write_operations = [
            "INSERT INTO public.test_readonly_table VALUES (2, 'test')",
            "UPDATE public.test_readonly_table SET value = 'updated' WHERE id = 1",
            "DELETE FROM public.test_readonly_table WHERE id = 1",
            "CREATE TABLE public.test_write_table (id INT)",
        ]

        for query in write_operations:
            pg_instance['custom_queries'] = [
                {
                    'query': query,
                    'columns': [{'name': 'result', 'type': 'gauge'}],
                    'metric_prefix': 'postgres',
                }
            ]

            aggregator = dd_agent_check(pg_instance)

            # Write queries should fail, so no metrics should be submitted
            metrics = list(aggregator.metrics('postgres.result'))
            assert len(metrics) == 0, f"Write query succeeded but should have been blocked: {query}"

        # Verify database state unchanged
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.test_readonly_table")
            assert cur.fetchone()[0] == 1, "Database was modified despite read-only mode"
    finally:
        with conn.cursor() as cur:
            cur.execute(f"REVOKE CREATE ON SCHEMA public FROM {pg_instance['username']}")
            cur.execute("DROP TABLE IF EXISTS public.test_readonly_table")
            cur.execute("DROP TABLE IF EXISTS public.test_write_table")
            conn.commit()
        conn.close()


@pytest.mark.e2e
def test_custom_queries_readonly_allows_reads(dd_agent_check, pg_instance):
    """Verify that read operations work normally in read-only mode"""
    pg_instance['custom_queries'] = [
        {
            'query': 'SELECT 1 as test_value',
            'columns': [{'name': 'test_value', 'type': 'gauge'}],
            'metric_prefix': 'postgres',
        }
    ]

    aggregator = dd_agent_check(pg_instance)
    aggregator.assert_metric('postgres.test_value', value=1)
