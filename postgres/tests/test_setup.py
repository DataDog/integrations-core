# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Smoke tests for the DBM Postgres setup module.

These run against the live containerized Postgres provided by ``dd_environment``,
which the hatch matrix spins up once per supported server version (9.6 -> 18). The
goal is to prove that ``datadog_checks.postgres.setup`` *executes* correctly across
every version: the Detect/Plan SQL introspection runs without error, version
branching is correct, the stdin/stdout contract the Go agent relies on works, and a
real Apply is idempotent on re-runs.
"""

import json
import subprocess
import sys

import psycopg
import pytest

from datadog_checks.postgres import setup

from .common import DB_NAME, HOST, PASSWORD_ADMIN, PORT, POSTGRES_VERSION, USER_ADMIN

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]

SMOKE_USER = 'dd_setup_smoke'
SMOKE_PASSWORD = 'dd_setup_smoke'

ADMIN_URI = f"postgresql://{USER_ADMIN}:{PASSWORD_ADMIN}@{HOST}:{PORT}/{DB_NAME}"


def _admin_connect(dbname=DB_NAME):
    """Autocommit superuser connection for test fixtures/teardown (not via the module)."""
    return psycopg.connect(
        host=HOST, port=PORT, user=USER_ADMIN, password=PASSWORD_ADMIN, dbname=dbname, autocommit=True
    )


def _run(config):
    return setup.run_setup({"connection_uri": ADMIN_URI, "config": config})


def _op_types(result):
    return {op.get("op_type") for op in result["operations"]}


def _failed_ops(result):
    return [op for op in result["operations"] if op.get("status") == "failed"]


def _expected_major():
    """The major version we expect the module to detect, or None when unknown (latest/unpinned)."""
    try:
        return int(float(POSTGRES_VERSION))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Dry run — the core version smoke test. Exercises all live Detect/Plan SQL
# against every server version with zero mutation.
# ---------------------------------------------------------------------------


def test_setup_dry_run_across_versions():
    result = _run(
        {
            "datadog_user": "datadog",  # pre-created by the test fixtures, so no password needed
            "databases": [DB_NAME],
            "dry_run": True,
        }
    )

    assert result["outcome"] == "dry_run"
    assert result["flavor"] == "self_hosted"
    assert not _failed_ops(result)

    major = result["pg_version"]
    assert isinstance(major, int) and major >= 9
    expected = _expected_major()
    if expected is not None:
        assert major == expected

    # Version-specific grant branch: pg_monitor exists on 10+, table grants on 9.6.
    op_types = _op_types(result)
    if major >= 10:
        assert "grant_pg_monitor" in op_types
        assert "grant_pg96" not in op_types
    else:
        assert "grant_pg96" in op_types
        assert "grant_pg_monitor" not in op_types

    # Per-database objects are always planned for the requested database.
    for expected_op in ("create_extension", "create_schema", "func_explain_statement"):
        assert expected_op in op_types


def test_setup_rejects_read_replica_detection_path():
    """Detect runs pg_is_in_recovery() on every version; on a primary it must not raise."""
    result = _run({"datadog_user": "datadog", "databases": [DB_NAME], "dry_run": True})
    # Reaching a dry_run result at all proves the primary/standby probe executed and passed.
    assert result["outcome"] == "dry_run"


# ---------------------------------------------------------------------------
# stdin/stdout contract — the actual interface the Go agent tunnels into.
# ---------------------------------------------------------------------------


def test_setup_cli_stdin_stdout_contract():
    payload = json.dumps(
        {
            "connection_uri": ADMIN_URI,
            "config": {"datadog_user": "datadog", "databases": [DB_NAME], "dry_run": True},
        }
    )
    proc = subprocess.run(
        [sys.executable, "-m", "datadog_checks.postgres.setup"],
        input=payload,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    envelope = json.loads(proc.stdout)
    assert envelope["success"] is True
    assert envelope["result"]["outcome"] == "dry_run"


def test_setup_cli_reports_failure_nonzero():
    """A bad connection must surface as success=False and a non-zero exit code."""
    payload = json.dumps(
        {
            "connection_uri": f"postgresql://{USER_ADMIN}:wrong-password@{HOST}:{PORT}/{DB_NAME}",
            "config": {"datadog_user": "datadog", "databases": [DB_NAME], "dry_run": True},
        }
    )
    proc = subprocess.run(
        [sys.executable, "-m", "datadog_checks.postgres.setup"],
        input=payload,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    envelope = json.loads(proc.stdout)
    assert envelope["success"] is False
    assert envelope["error"]


# ---------------------------------------------------------------------------
# Real apply + idempotency. Creates a throwaway user and real DB objects, then
# re-runs to prove the second pass is a clean no-op (the RDS/Aurora re-run fix).
# ---------------------------------------------------------------------------


@pytest.fixture
def smoke_user_cleanup():
    yield
    with _admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (SMOKE_USER,))
            if cur.fetchone():
                # Drop privileges the user was granted (schema usage, etc.) before dropping the role.
                cur.execute(f'DROP OWNED BY "{SMOKE_USER}"')
                cur.execute(f'DROP ROLE "{SMOKE_USER}"')
    # Restore the only server-global settings a self-hosted apply can touch here.
    with _admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER SYSTEM RESET track_activity_query_size")
            cur.execute('ALTER SYSTEM RESET "pg_stat_statements.track_utility"')
            cur.execute("SELECT pg_reload_conf()")


def test_setup_apply_and_idempotency(smoke_user_cleanup):
    config = {
        "datadog_user": SMOKE_USER,
        "datadog_password": SMOKE_PASSWORD,
        "databases": [DB_NAME],
    }

    first = _run(config)
    assert first["outcome"] in ("success", "success_with_manual_steps")
    assert not _failed_ops(first), _failed_ops(first)

    # The user did not exist, so it must have been created and granted monitoring access.
    create_user = next(op for op in first["operations"] if op.get("op_type") == "create_user")
    assert create_user["status"] == "completed"
    # Password must be redacted from the recorded operation.
    assert create_user.get("redact") is True

    # The role really exists and can authenticate now.
    with psycopg.connect(host=HOST, port=PORT, user=SMOKE_USER, password=SMOKE_PASSWORD, dbname=DB_NAME) as conn:
        assert conn.info.status is not None

    # Second run: nothing should fail, and the user is now detected as existing (no re-create).
    second = _run(config)
    assert second["outcome"] in ("success", "success_with_manual_steps")
    assert not _failed_ops(second), _failed_ops(second)
    assert "create_user" not in _op_types(second)
