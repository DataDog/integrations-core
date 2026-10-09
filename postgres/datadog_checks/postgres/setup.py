# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
DBM Postgres setup — Detect → Plan → Apply.

Invoked by ``datadog-agent integration setup postgres`` via the embedded Python
interpreter (``python -m datadog_checks.postgres.setup``). Reads a JSON config
from stdin and writes a JSON result to stdout, so the Go CLI stays a thin tunnel
that owns flags, prompts, exit codes, and output rendering while this module owns
all database logic.

Setup cannot run as part of the check the way ``diagnose`` does: it runs before
the instance config exists and connects as a superuser supplied on the CLI. It
does, however, reuse the same building blocks as the running check —
``configure_connection`` for psycopg setup, ``AUTODISCOVERY_QUERY`` for database
navigation, and ``parse_shared_preload_libraries`` — so setup connects and reasons
about the server exactly like the integration. The canonical ``datadog`` helper
function definitions live here as constants alongside the test compose resources,
so there is a single source of truth in this repository instead of a copy drifting
in the agent.
"""

import json
import sys

import psycopg
from psycopg import sql

from .connection_pool import configure_connection
from .discovery import AUTODISCOVERY_QUERY
from .util import parse_shared_preload_libraries

# (name, desired_value, requires_restart, required)
# required=False means the setting is optional per DBM docs — DBM works without it,
# but it improves query coverage and performance visibility.
#
# pg_stat_statements.max is intentionally excluded. It can only be set after
# pg_stat_statements is loaded (which requires a restart), and it is itself a
# postmaster-context GUC that requires a second restart. Requiring two restarts
# on a fresh install is poor UX; the PostgreSQL default of 5000 is sufficient
# for most deployments.
SETTINGS = [
    ("shared_preload_libraries", "pg_stat_statements", True, True),
    ("track_activity_query_size", "4096", True, True),
    ("pg_stat_statements.track", "all", False, False),
    ("track_io_timing", "on", False, False),
    ("pg_stat_statements.track_utility", "on", False, False),
]

# Canonical definitions of the datadog helper functions. Kept verbatim in sync with
# tests/compose/resources/03_setup.sh so the setup CLI and the test fixtures agree.
SQL_FUNC_PG_STAT_ACTIVITY = """
CREATE OR REPLACE FUNCTION datadog.pg_stat_activity() RETURNS SETOF pg_stat_activity AS
  $$ SELECT * FROM pg_catalog.pg_stat_activity; $$
LANGUAGE sql SECURITY DEFINER"""

SQL_FUNC_PG_STAT_STATEMENTS = """
CREATE OR REPLACE FUNCTION datadog.pg_stat_statements() RETURNS SETOF pg_stat_statements AS
  $$ SELECT * FROM pg_stat_statements; $$
LANGUAGE sql SECURITY DEFINER"""

SQL_FUNC_EXPLAIN_STATEMENT = """
CREATE OR REPLACE FUNCTION datadog.explain_statement(
    l_query TEXT,
    OUT explain JSON
)
RETURNS SETOF JSON AS
$$
DECLARE
curs REFCURSOR;
plan JSON;

BEGIN
    SET TRANSACTION READ ONLY;

    OPEN curs FOR EXECUTE pg_catalog.concat('EXPLAIN (FORMAT JSON) ', l_query);
    FETCH curs INTO plan;
    CLOSE curs;
    RETURN QUERY SELECT plan;
END;
$$
LANGUAGE 'plpgsql'
RETURNS NULL ON NULL INPUT
SECURITY DEFINER"""


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------


def _connect(uri, dbname=None):
    """Open a psycopg (v3) connection configured like the running check.

    ``configure_connection`` sets autocommit, SQL_ASCII text decoding, and the
    CommenterCursor cursor factory. CommenterCursor subclasses ClientCursor, which
    is required — not just stylistic: PostgreSQL rejects server-side bound parameters
    in utility statements (CREATE USER ... WITH PASSWORD %s), so client-side binding
    is mandatory for setup. ``dbname``, when given, overrides the database in ``uri``
    for per-database operations.
    """
    kwargs = {"dbname": dbname} if dbname else {}
    conn = psycopg.connect(uri, **kwargs)
    configure_connection(conn)
    return conn


def _query(cur, composed):
    """Render a psycopg.sql composition to a plain string. CommenterCursor runs
    add_sql_comment(), which calls .strip() on the query, so it needs a str —
    not a sql.Composed. Identifiers stay safely quoted by as_string()."""
    return composed.as_string(cur)


# ---------------------------------------------------------------------------
# Detect
# ---------------------------------------------------------------------------


def _detect(cur, config):
    # Fail immediately if connected to a standby/read replica.
    cur.execute("SELECT pg_is_in_recovery()")
    if cur.fetchone()[0]:
        raise RuntimeError(
            "Connected to a read replica (pg_is_in_recovery() = true); connect to the primary instance to run setup"
        )

    flavor = _detect_flavor(cur)
    pg_version = _detect_version(cur)
    current_settings, pending_restart = _detect_settings(cur)
    user_exists = _detect_user_exists(cur, config["datadog_user"])
    databases = _detect_databases(cur, config)

    return {
        "flavor": flavor,
        "pg_version": pg_version,
        "user_exists": user_exists,
        "current_settings": current_settings,
        "pending_restart": pending_restart,
        "databases": databases,
    }


def _detect_flavor(cur):
    if _role_exists(cur, "cloudsqladmin"):
        return "cloud_sql"
    if _role_exists(cur, "azure_superuser"):
        return "azure"

    try:
        cur.execute("SELECT current_setting('rds.extensions', true)")
        result = cur.fetchone()
        if result and result[0]:
            cur.execute("SELECT version()")
            version_str = cur.fetchone()[0]
            return "aurora" if "Aurora" in version_str else "rds"
    except psycopg.Error:
        # rds.extensions is an RDS-specific GUC; a plain Postgres rejects it. Any
        # other error (network blip, permissions) should surface rather than be
        # silently treated as self-hosted, so only swallow psycopg errors here.
        pass

    return "self_hosted"


def _role_exists(cur, rolname):
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (rolname,))
    return cur.fetchone() is not None


def _detect_version(cur):
    cur.execute("SHOW server_version_num")
    return int(cur.fetchone()[0]) // 10000


def _detect_settings(cur):
    cur.execute("""
        SELECT name, setting, pending_restart
        FROM pg_settings
        WHERE name IN (
            'shared_preload_libraries', 'track_activity_query_size',
            'pg_stat_statements.max', 'pg_stat_statements.track',
            'track_io_timing', 'pg_stat_statements.track_utility'
        )
    """)
    current_settings = {}
    pending_restart = []
    for name, setting, is_pending in cur.fetchall():
        current_settings[name] = setting
        if is_pending:
            pending_restart.append(name)
    return current_settings, pending_restart


def _detect_user_exists(cur, username):
    return _role_exists(cur, username)


def _detect_databases(cur, config):
    if config.get("all_databases"):
        # Reuse the integration's autodiscovery query; sort for stable output.
        cur.execute(AUTODISCOVERY_QUERY)
        return sorted(row[0] for row in cur.fetchall())
    return config.get("databases", [])


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def _plan(state, config):
    ops = []
    ops.extend(_plan_user_ops(state, config))
    ops.extend(_plan_grant_ops(state, config))
    setting_ops, optional_restart_pending = _plan_setting_ops(state, config)
    ops.extend(setting_ops)
    for db in state["databases"]:
        ops.extend(_plan_per_db_ops(config, db))
    return ops, optional_restart_pending


def _plan_user_ops(state, config):
    user = config["datadog_user"]
    if not state["user_exists"]:
        if not config.get("datadog_password"):
            raise RuntimeError(f"--datadog-password is required when creating user {user!r} for the first time")
        return [
            {
                "kind": "SQL",
                "description": f"create user {user!r}",
                "op_type": "create_user",
                "args": [user, config["datadog_password"]],
                "redact": True,
            }
        ]
    if config.get("datadog_password") and config.get("update_password"):
        return [
            {
                "kind": "SQL",
                "description": f"sync password for user {user!r}",
                "op_type": "alter_user_password",
                "args": [user, config["datadog_password"]],
                "redact": True,
            }
        ]
    return [{"kind": "SKIP", "description": f"user {user!r} — already exists", "status": "skipped"}]


def _plan_grant_ops(state, config):
    user = config["datadog_user"]
    ops = []
    if state["pg_version"] >= 10:
        ops.append(
            {
                "kind": "SQL",
                "description": f"GRANT pg_monitor TO {user!r}",
                "op_type": "grant_pg_monitor",
                "args": [user],
            }
        )
    else:
        ops.append(
            {
                "kind": "SQL",
                "description": f"GRANT pg_stat_* tables to {user!r} (PG 9.6)",
                "op_type": "grant_pg96",
                "args": [user],
            }
        )
    if state["pg_version"] >= 15 and state["flavor"] in ("rds", "aurora"):
        ops.append(
            {
                "kind": "SQL",
                "description": f"ALTER ROLE {user!r} INHERIT (RDS/Aurora PG 15+)",
                "op_type": "alter_role_inherit",
                "args": [user],
            }
        )
    return ops


def _plan_setting_ops(state, config):
    # pg_stat_statements GUCs are only registered after the library is loaded.
    # pg_stat_statements explicitly blocks mid-session LOAD, so these GUCs
    # cannot be set until after the first restart that loads the library.
    spl_active = state["current_settings"].get("shared_preload_libraries", "")
    pg_stat_loaded = "pg_stat_statements" in parse_shared_preload_libraries(spl_active)

    apply_optional_restart = config.get("apply_optional_restart", False)

    ops = []
    optional_restart_pending = []

    for name, desired, requires_restart, required in SETTINGS:
        current = state["current_settings"].get(name, "")
        flavor = state["flavor"]

        # Skip pg_stat_statements.* GUCs until the library is loaded.
        if flavor == "self_hosted" and name.startswith("pg_stat_statements.") and not pg_stat_loaded:
            ops.append(
                {
                    "kind": "SKIP",
                    "description": f"{name} — applied on next run after pg_stat_statements loads",
                    "setting_name": name,
                    "status": "skipped",
                }
            )
            continue

        # Optional restart-required settings: skip unless explicitly requested.
        if not required and requires_restart and flavor == "self_hosted":
            if not apply_optional_restart:
                # Check if it already has the desired value before deferring.
                if current == desired or (name == "shared_preload_libraries" and desired in current.split(",")):
                    pass  # already set — fall through to normal planning (will show SKIP)
                else:
                    optional_restart_pending.append(
                        {
                            "name": name,
                            "desired": desired,
                            "current": current,
                            "description": f"optional — set {name}={desired} (requires one more restart)",
                        }
                    )
                    ops.append(
                        {
                            "kind": "SKIP",
                            "description": f"{name} — optional, skipped (add --yes to apply, requires restart)",
                            "setting_name": name,
                            "status": "skipped",
                        }
                    )
                    continue

        if flavor == "self_hosted":
            ops.extend(_plan_self_hosted_setting(state, name, desired, current, requires_restart))
        elif flavor in ("rds", "aurora"):
            ops.extend(_plan_aws_setting(name, desired, current))
        elif flavor == "cloud_sql":
            ops.extend(_plan_cloud_sql_setting(name, desired, current))
        elif flavor == "azure":
            ops.extend(_plan_azure_setting(name, desired, current))

    return ops, optional_restart_pending


def _plan_self_hosted_setting(state, name, desired, current, requires_restart):
    if name == "shared_preload_libraries":
        return _plan_spl(state, desired, current)
    if current == desired:
        return [_skip_setting(name, f"{name} = {desired} — already set")]
    if name in state["pending_restart"]:
        return [_skip_setting(name, f"{name} — restart already pending, skipping ALTER SYSTEM")]
    kind = "ALTER_SYSTEM" if requires_restart else "ALTER_SYSTEM_RELOAD"
    return [
        {
            "kind": kind,
            "description": f"ALTER SYSTEM SET {name} = '{desired}'",
            "sql": f"ALTER SYSTEM SET {name} = '{desired}'",
            "setting_name": name,
            "requires_restart": requires_restart,
        }
    ]


def _plan_spl(state, desired, current):
    libs = parse_shared_preload_libraries(current)
    if desired in libs:
        return [_skip_setting("shared_preload_libraries", f"shared_preload_libraries already contains '{desired}'")]
    if "shared_preload_libraries" in state["pending_restart"]:
        return [
            _skip_setting(
                "shared_preload_libraries",
                "shared_preload_libraries — restart already pending; check postgresql.auto.conf before restarting",
            )
        ]
    new_value = f"{current},{desired}" if current else desired
    return [
        {
            "kind": "ALTER_SYSTEM",
            "description": f"ALTER SYSTEM SET shared_preload_libraries = '{new_value}'",
            "sql": f"ALTER SYSTEM SET shared_preload_libraries = '{new_value}'",
            "setting_name": "shared_preload_libraries",
            "requires_restart": True,
        }
    ]


def _plan_aws_setting(name, desired, current):
    # Idempotent re-runs: once the user has applied the parameter-group change,
    # current == desired (or the library is already loaded), so skip instead of
    # emitting a MANUAL_STEP forever and exiting non-zero.
    if name == "shared_preload_libraries" and desired in parse_shared_preload_libraries(current):
        return [_skip_setting(name, f"shared_preload_libraries already contains '{desired}' — skipped")]
    if current == desired:
        return [_skip_setting(name, f"{name} = {desired} — already set")]
    instruction = (
        f"Set {name} = '{desired}'\n    → RDS Console → Parameter Groups → your group → save → reboot instance"
    )
    return [_manual_step(name, f"[AWS Parameter Group] {name} = '{desired}'", instruction)]


def _plan_cloud_sql_setting(name, desired, current):
    if name == "shared_preload_libraries":
        return [_skip_setting(name, "shared_preload_libraries — pre-loaded on Cloud SQL")]
    if current == desired:
        return [_skip_setting(name, f"{name} = {desired} — already set")]
    instruction = (
        f"Set {name} = '{desired}'\n"
        f"    → Cloud SQL Console → your instance → Edit → Database flags → save → restart instance"
    )
    return [_manual_step(name, f"[Cloud SQL Database Flag] {name} = '{desired}'", instruction)]


def _plan_azure_setting(name, desired, current):
    if name == "shared_preload_libraries" and desired in parse_shared_preload_libraries(current):
        return [_skip_setting(name, f"shared_preload_libraries already contains '{desired}' — skipped")]
    if current == desired:
        return [_skip_setting(name, f"{name} = {desired} — already set")]
    instruction = (
        f"Set {name} = '{desired}'\n    → Azure Portal → your server → Server parameters → save → restart if required"
    )
    return [_manual_step(name, f"[Azure Server Parameters] {name} = '{desired}'", instruction)]


def _skip_setting(name, description):
    return {"kind": "SKIP", "description": description, "setting_name": name, "status": "skipped"}


def _manual_step(name, description, instruction):
    return {
        "kind": "MANUAL_STEP",
        "description": description,
        "setting_name": name,
        "manual_instruction": instruction,
        "status": "manual",
    }


def _plan_per_db_ops(config, db):
    user = config["datadog_user"]
    return [
        {
            "kind": "SQL",
            "description": "CREATE EXTENSION IF NOT EXISTS pg_stat_statements",
            "op_type": "create_extension",
            "database": db,
        },
        {
            "kind": "SQL",
            "description": "CREATE SCHEMA IF NOT EXISTS datadog",
            "op_type": "create_schema",
            "database": db,
        },
        {
            "kind": "SQL",
            "description": f"GRANT USAGE ON SCHEMA datadog TO {user!r}",
            "op_type": "grant_schema_usage",
            "args": [user],
            "database": db,
        },
        {
            "kind": "SQL",
            "description": "CREATE OR REPLACE FUNCTION datadog.pg_stat_activity()",
            "op_type": "func_pg_stat_activity",
            "database": db,
        },
        {
            "kind": "SQL",
            "description": "CREATE OR REPLACE FUNCTION datadog.pg_stat_statements()",
            "op_type": "func_pg_stat_statements",
            "database": db,
        },
        {
            "kind": "SQL",
            "description": "CREATE OR REPLACE FUNCTION datadog.explain_statement()",
            "op_type": "func_explain_statement",
            "database": db,
        },
    ]


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def _execute_op(cur, op):
    """Execute a single operation using psycopg (v3) with safe identifier handling."""
    op_type = op.get("op_type")
    args = op.get("args", [])

    if op_type == "create_user":
        cur.execute(
            _query(cur, sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(args[0]))),
            (args[1],),
        )
    elif op_type == "alter_user_password":
        cur.execute(
            _query(cur, sql.SQL("ALTER USER {} WITH PASSWORD %s").format(sql.Identifier(args[0]))),
            (args[1],),
        )
    elif op_type == "grant_pg_monitor":
        cur.execute(_query(cur, sql.SQL("GRANT pg_monitor TO {}").format(sql.Identifier(args[0]))))
    elif op_type == "grant_pg96":
        cur.execute(
            _query(
                cur,
                sql.SQL(
                    "GRANT SELECT ON pg_stat_database TO {};"
                    "GRANT SELECT ON pg_stat_database_conflicts TO {};"
                    "GRANT SELECT ON pg_stat_bgwriter TO {}"
                ).format(
                    sql.Identifier(args[0]),
                    sql.Identifier(args[0]),
                    sql.Identifier(args[0]),
                ),
            )
        )
    elif op_type == "alter_role_inherit":
        cur.execute(_query(cur, sql.SQL("ALTER ROLE {} INHERIT").format(sql.Identifier(args[0]))))
    elif op_type == "create_extension":
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
    elif op_type == "create_schema":
        cur.execute("CREATE SCHEMA IF NOT EXISTS datadog")
    elif op_type == "grant_schema_usage":
        cur.execute(_query(cur, sql.SQL("GRANT USAGE ON SCHEMA datadog TO {}").format(sql.Identifier(args[0]))))
    elif op_type == "func_pg_stat_activity":
        cur.execute(SQL_FUNC_PG_STAT_ACTIVITY)
    elif op_type == "func_pg_stat_statements":
        cur.execute(SQL_FUNC_PG_STAT_STATEMENTS)
    elif op_type == "func_explain_statement":
        cur.execute(SQL_FUNC_EXPLAIN_STATEMENT)
    elif "sql" in op:
        cur.execute(op["sql"])
    else:
        raise RuntimeError(f"Unknown op_type: {op_type!r}")


def _apply(ops, uri, state, optional_restart_pending=None):
    base_conn = _connect(uri)

    db_conns = {}
    failed = False

    try:
        for op in ops:
            if op.get("status") in ("skipped", "manual"):
                continue
            if op["kind"] == "MANUAL_STEP":
                op["status"] = "manual"
                continue
            if op["kind"] == "SKIP":
                op["status"] = "skipped"
                continue
            if failed:
                op["status"] = "pending"
                continue

            db = op.get("database")
            try:
                if db:
                    if db not in db_conns:
                        db_conns[db] = _connect(uri, dbname=db)
                    conn = db_conns[db]
                else:
                    conn = base_conn

                cur = conn.cursor()
                _execute_op(cur, op)

                if op["kind"] == "ALTER_SYSTEM_RELOAD":
                    base_conn.cursor().execute("SELECT pg_reload_conf()")

                op["status"] = "completed"
            except Exception as exc:
                op["status"] = "failed"
                op["error"] = str(exc)
                failed = True
    finally:
        for c in db_conns.values():
            try:
                c.close()
            except Exception:
                pass
        base_conn.close()

    return _build_result(ops, state, failed, optional_restart_pending)


def _build_result(ops, state, failed, optional_restart_pending=None):
    manual_steps = any(op["kind"] == "MANUAL_STEP" for op in ops)
    restart_needed = any(op.get("requires_restart") and op.get("status") == "completed" for op in ops) or bool(
        state.get("pending_restart")
    )
    if failed:
        outcome = "failure"
    elif manual_steps or restart_needed:
        outcome = "success_with_manual_steps"
    else:
        outcome = "success"
    return {
        "operations": ops,
        "flavor": state["flavor"],
        "pg_version": state["pg_version"],
        "restart_needed": restart_needed,
        "manual_steps": manual_steps,
        "outcome": outcome,
        "optional_restart_pending": optional_restart_pending or [],
    }


def _dry_run_result(ops, state, optional_restart_pending=None):
    for op in ops:
        if op.get("status") == "skipped" or op["kind"] == "SKIP":
            op["status"] = "skipped"
        elif op["kind"] == "MANUAL_STEP":
            op["status"] = "manual"
        else:
            op["status"] = "pending"
    manual_steps = any(op["kind"] == "MANUAL_STEP" for op in ops)
    return {
        "operations": ops,
        "flavor": state["flavor"],
        "pg_version": state["pg_version"],
        "restart_needed": False,
        "manual_steps": manual_steps,
        "outcome": "dry_run",
        "optional_restart_pending": optional_restart_pending or [],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_setup(args):
    """Run Detect → Plan → Apply for the given parsed JSON args and return the result dict."""
    uri = args["connection_uri"]
    config = args["config"]

    conn = _connect(uri)
    try:
        state = _detect(conn.cursor(), config)
    finally:
        conn.close()

    if not state["user_exists"] and not config.get("datadog_password"):
        raise RuntimeError(
            f"--datadog-password is required when creating user {config['datadog_user']!r} for the first time"
        )

    ops, optional_restart_pending = _plan(state, config)

    if config.get("dry_run"):
        return _dry_run_result(ops, state, optional_restart_pending)
    return _apply(ops, uri, state, optional_restart_pending)


def main():
    args = json.loads(sys.stdin.read())
    try:
        result = run_setup(args)
        print(json.dumps({"success": True, "result": result}))
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
