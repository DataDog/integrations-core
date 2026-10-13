# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

# Databases the agent lacks CONNECT on (for example after REVOKE CONNECT ... FROM PUBLIC) are reported so the
# collector can skip them instead of failing to connect on every run.
QUERY_LIST_DATABASES = """
SELECT d.datname::text AS database_name,
       pg_catalog.has_database_privilege(d.oid, 'CONNECT') AS can_connect
FROM pg_catalog.pg_database AS d
WHERE d.datallowconn
  AND NOT d.datistemplate
  AND {database_filter}
ORDER BY database_name
"""


def list_databases_query(database_filter: str = "TRUE") -> str:
    """Build the database discovery query with a collector-generated filter."""
    return QUERY_LIST_DATABASES.format(database_filter=database_filter)


# Built-in settings have no dot in their name. Every dotted setting belongs to an extension or application, and
# those can hold secrets such as `pgrst.jwt_secret` or `anon.salt`, whether or not a loaded module registers them.
# Dotted settings are collected only for extensions known to hold no secrets; all others are skipped entirely.
ROLE_SETTING_VALUE_PREFIXES = ("auto_explain", "pg_hint_plan", "pg_stat_statements", "pgaudit", "plpgsql")

# Before PostgreSQL 16, inheritance is a property of the member, and every membership allows SET ROLE to the group.
MEMBERSHIP_OPTIONS_PRE_PG16 = """',"member_can_inherit":' || member_role.rolinherit::text
               || ',"member_can_set":true}'"""
MEMBERSHIP_OPTIONS_PG16_PLUS = """',"member_can_inherit":' || membership.inherit_option::text
               || ',"member_can_set":' || membership.set_option::text || '}'"""


def _roles_query(membership_options: str, member_role_join: str) -> str:
    # One row per role, with the memberships where it is the member and its settings nested as JSON text. Both are
    # aggregated once per role and joined: pg_db_role_setting has no index on the role alone, so looking settings up
    # per role would scan the whole table for every role. Dropping a role leaves memberships it granted pointing at
    # its OID before PostgreSQL 16, so a grantor OID can be missing from `roles`. setrole 0 holds settings that apply
    # to every role in a database. The settings allowlist is the query's only parameter; prefixes are matched
    # case-insensitively because custom setting names keep the case they were written in.
    return f"""
SELECT r.rolname::text AS role_name,
       r.oid::bigint AS role_oid,
       r.rolsuper AS is_super,
       r.rolinherit AS can_inherit,
       r.rolcreaterole AS can_create_role,
       r.rolcreatedb AS can_create_db,
       r.rolcanlogin AS can_login,
       r.rolreplication AS is_replication,
       r.rolbypassrls AS can_bypass_rls,
       r.rolconnlimit AS conn_limit,
       pg_catalog.to_json(r.rolvaliduntil) AS valid_until,
       '[' || COALESCE(memberships.entries, '') || ']' AS member_of,
       '[' || COALESCE(role_settings.entries, '') || ']' AS settings
FROM pg_catalog.pg_roles AS r
LEFT JOIN (
    SELECT membership.member,
           pg_catalog.string_agg(
               '{{"group_role_oid":' || membership.roleid::bigint::text
               || ',"grantor_role_oid":' || membership.grantor::bigint::text
               || ',"admin_option":' || membership.admin_option::text
               || {membership_options},
               ',') AS entries
    FROM pg_catalog.pg_auth_members AS membership{member_role_join}
    GROUP BY membership.member
) AS memberships
  ON memberships.member = r.oid
LEFT JOIN (
    SELECT settings.setrole,
           pg_catalog.string_agg(
               '{{"database_name":' || pg_catalog.to_json(COALESCE(database.datname::text, ''))::text
               || ',"setting_name":' || pg_catalog.to_json(parsed.setting_name)::text
               || ',"setting_value":' || pg_catalog.to_json(parsed.setting_value)::text || '}}',
               ',') AS entries
    FROM pg_catalog.pg_db_role_setting AS settings
    CROSS JOIN LATERAL unnest(settings.setconfig) AS setting
    CROSS JOIN LATERAL (
        SELECT split_part(setting, '=', 1) AS setting_name,
               substr(setting, strpos(setting, '=') + 1) AS setting_value
    ) AS parsed
    LEFT JOIN pg_catalog.pg_database AS database
      ON database.oid = settings.setdatabase
    WHERE settings.setrole <> 0
      AND (
          strpos(parsed.setting_name, '.') = 0
          OR lower(split_part(parsed.setting_name, '.', 1)) = ANY(%s)
      )
    GROUP BY settings.setrole
) AS role_settings
  ON role_settings.setrole = r.oid
"""


ROLES_QUERIES = {
    True: _roles_query(MEMBERSHIP_OPTIONS_PG16_PLUS, ""),
    False: _roles_query(
        MEMBERSHIP_OPTIONS_PRE_PG16,
        "\n    JOIN pg_catalog.pg_roles AS member_role\n      ON member_role.oid = membership.member",
    ),
}


def roles_query(*, pg16_plus: bool) -> str:
    """Select the roles query for the connected server version."""
    return ROLES_QUERIES[pg16_plus]


# Schemas role collection never reports: system catalogs, the information schema, the agent's own schema, and
# TOAST and temporary schemas.
EXCLUDED_SCHEMAS = ("pg_catalog", "information_schema", "datadog")
EXCLUDED_SCHEMA_PREFIXES = ("pg_toast", "pg_temp")


def _collected_schema(namespace: str) -> str:
    """Return the SQL condition that `namespace`, a `pg_namespace` alias, is a schema role collection reports.

    Every query branch filters through this one definition, so an object's privileges are always filtered like the
    object itself.
    """
    names = ", ".join(f"'{name}'" for name in EXCLUDED_SCHEMAS)
    conditions = [f"{namespace}.nspname NOT IN ({names})"]
    conditions.extend(f"{namespace}.nspname NOT LIKE '{prefix}%'" for prefix in EXCLUDED_SCHEMA_PREFIXES)
    return "\n      AND ".join(conditions)


RELATION_TYPE = """CASE relation.relkind
               WHEN 'r' THEN 'table'
               WHEN 'p' THEN 'partitioned_table'
               WHEN 'v' THEN 'view'
               WHEN 'm' THEN 'materialized_view'
               WHEN 'f' THEN 'foreign_table'
               WHEN 'S' THEN 'sequence'
           END"""

# Base, composite, domain, enum, and range types; multiranges and pseudo-types are created by Postgres. Composite
# types that are a table's or view's row type belong to that relation, and array types are created alongside each
# type.
COLLECTED_TYPE = """type.typtype IN ('b', 'c', 'd', 'e', 'r')
      AND (
          type.typrelid = 0
          OR EXISTS (
              SELECT 1
              FROM pg_catalog.pg_class AS relation
              WHERE relation.oid = type.typrelid
                AND relation.relkind = 'c'
          )
      )
      AND NOT EXISTS (
          SELECT 1
          FROM pg_catalog.pg_type AS element
          WHERE element.typarray = type.oid
      )"""

# PostgreSQL 11 added procedures and replaced proisagg and proiswindow with prokind. Earlier versions derive the
# same kind codes, so routine branches report the same object types on every version.
ROUTINE_KIND_PG11_PLUS = "routine.prokind"
ROUTINE_KIND_PRE_PG11 = "(CASE WHEN routine.proisagg THEN 'a' WHEN routine.proiswindow THEN 'w' ELSE 'f' END)"


def _routine_type(routine_kind: str) -> str:
    return f"""CASE {routine_kind}
               WHEN 'p' THEN 'procedure'
               WHEN 'a' THEN 'aggregate'
               ELSE 'function'
           END"""


ROUTINE_NAME = """(
               routine.proname
               || '('
               || pg_catalog.oidvectortypes(routine.proargtypes)
               || ')'
           )::text"""


# Nested arrays are built in the query as JSON text, which is much cheaper for Postgres than `json_agg` of a row,
# and returned as `text` so neither Postgres nor the agent parses them; the collector splices them into the payload.
# OIDs are numbers and privilege types are fixed keywords, so only names, which can hold any character, are escaped
# with `to_json`. Each element starts with a fixed key that `NESTED_ELEMENT_MARKERS` uses to count elements.
PRIVILEGE_ENTRY = """'{"column_name":' || :column_name_json
    || ',"grantee_oid":' || acl.grantee::text
    || ',"grantor_oid":' || acl.grantor::text
    || ',"privilege":"' || acl.privilege_type
    || CASE WHEN acl.is_grantable THEN '","is_grantable":true}' ELSE '","is_grantable":false}' END"""

GRANT_ENTRY = """'{"grantee_oid":' || acl.grantee::text
    || ',"grantor_oid":' || acl.grantor::text
    || ',"privilege":"' || acl.privilege_type
    || CASE WHEN acl.is_grantable THEN '","is_grantable":true}' ELSE '","is_grantable":false}' END"""

# The key each nested element starts with. JSON escapes every quote inside a string value, so these sequences can
# only appear at the start of an element, and counting them gives the number of elements without parsing.
NESTED_ELEMENT_MARKERS = {
    "privileges": '{"column_name":',
    "reads_from": '{"schema_name":',
    "grants": '{"grantee_oid":',
    "member_of": '{"group_role_oid":',
    "settings": '{"database_name":',
}


def _privilege_entries(acl_column: str, column_name_json: str = "'\"\"'") -> str:
    """Return a subquery producing the comma-separated JSON entries of `acl_column`, or NULL if it has none."""
    entry = PRIVILEGE_ENTRY.replace(":column_name_json", column_name_json)
    return f"""(SELECT pg_catalog.string_agg({entry}, ',')
            FROM pg_catalog.aclexplode({acl_column}) AS acl)"""


def _json_array(entries: str) -> str:
    return f"('[' || COALESCE({entries}, '') || ']')"


COLUMN_PRIVILEGE_ENTRY = PRIVILEGE_ENTRY.replace(
    ":column_name_json", "pg_catalog.to_json(attribute.attname::text)::text"
)

# Column grants exist on few relations. The IN check is evaluated once per query and kept in memory, so the
# per-relation pg_attribute lookup only runs for relations that have column grants. Sequences cannot have them.
RELATION_PRIVILEGES = f"""('[' || pg_catalog.concat_ws(',',
               {_privilege_entries("relation.relacl")},
               CASE
                   WHEN relation.relkind <> 'S'
                    AND relation.oid IN (
                        SELECT attrelid FROM pg_catalog.pg_attribute WHERE attacl IS NOT NULL
                    )
                   THEN (
                       SELECT pg_catalog.string_agg({COLUMN_PRIVILEGE_ENTRY}, ',')
                       FROM pg_catalog.pg_attribute AS attribute
                       CROSS JOIN LATERAL pg_catalog.aclexplode(attribute.attacl) AS acl
                       WHERE attribute.attrelid = relation.oid
                         AND attribute.attnum > 0
                         AND NOT attribute.attisdropped
                         AND attribute.attacl IS NOT NULL
                   )
               END
           ) || ']')"""

# The relations a view or materialized view reads, limited to relations role collection also reports.
RELATION_READS_FROM = f"""CASE
               WHEN relation.relkind IN ('v', 'm') THEN (
                   SELECT '[' || COALESCE(pg_catalog.string_agg(
                       '{{"schema_name":' || pg_catalog.to_json(referenced.schema_name)::text
                       || ',"object_name":' || pg_catalog.to_json(referenced.object_name)::text
                       || ',"object_type":"' || referenced.object_type || '"}}',
                       ','), '') || ']'
                   FROM (
                       SELECT DISTINCT
                              referenced_namespace.nspname::text AS schema_name,
                              referenced.relname::text AS object_name,
                              {RELATION_TYPE.replace("relation.relkind", "referenced.relkind")} AS object_type
                       FROM pg_catalog.pg_rewrite AS rewrite
                       JOIN pg_catalog.pg_depend AS dependency
                         ON dependency.objid = rewrite.oid
                        AND dependency.classid = 'pg_catalog.pg_rewrite'::pg_catalog.regclass
                        AND dependency.refclassid = 'pg_catalog.pg_class'::pg_catalog.regclass
                       JOIN pg_catalog.pg_class AS referenced
                         ON referenced.oid = dependency.refobjid
                       JOIN pg_catalog.pg_namespace AS referenced_namespace
                         ON referenced_namespace.oid = referenced.relnamespace
                       WHERE rewrite.ev_class = relation.oid
                         AND dependency.deptype = 'n'
                         AND referenced.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
                         AND referenced.oid <> relation.oid
                         AND {_collected_schema("referenced_namespace")}
                   ) AS referenced
               )
               ELSE '[]'
           END"""


DEFAULT_PRIVILEGE_GRANTS = _json_array(
    f"(SELECT pg_catalog.string_agg({GRANT_ENTRY}, ',') FROM pg_catalog.aclexplode(default_acl.defaclacl) AS acl)"
)

# One row per default-privilege rule: pg_default_acl is unique on owner, schema, and object type.
QUERY_DEFAULT_PRIVILEGES = f"""
SELECT default_acl.defaclrole::bigint AS owner_oid,
       COALESCE(namespace.nspname::text, '') AS schema_name,
       CASE default_acl.defaclobjtype
           WHEN 'r' THEN 'table'
           WHEN 'S' THEN 'sequence'
           WHEN 'f' THEN 'function'
           WHEN 'T' THEN 'type'
           WHEN 'n' THEN 'schema'
       END AS object_type,
       {DEFAULT_PRIVILEGE_GRANTS} AS grants
FROM pg_catalog.pg_default_acl AS default_acl
LEFT JOIN pg_catalog.pg_namespace AS namespace
  ON namespace.oid = default_acl.defaclnamespace
WHERE default_acl.defaclobjtype IN ('r', 'S', 'f', 'T', 'n')
  AND (
      default_acl.defaclnamespace = 0
      OR (
          {_collected_schema("namespace")}
      )
  )
"""


def _objects_query(routine_kind: str) -> str:
    # Each row is one object with its explicitly stored ACL entries nested in `privileges`, including column grants.
    # An object with a NULL ACL has the compiled-in default privileges for its type and owner; it has no entries of
    # its own and reports `has_default_acl` so the backend can resolve them. Column grants are stored only on
    # columns granted individually: table-level grants never populate `attacl`, and columns have no default
    # privileges, so a column grant adds access on top of the relation's own privileges.
    return f"""
SELECT objects.object_type,
       objects.schema_name,
       objects.object_name,
       objects.object_oid,
       objects.owner_oid,
       objects.is_security_definer,
       objects.security_invoker,
       objects.has_default_acl,
       objects.privileges,
       objects.reads_from
FROM (
    SELECT {RELATION_TYPE} AS object_type,
           namespace.nspname::text AS schema_name,
           relation.relname::text AS object_name,
           relation.oid::bigint AS object_oid,
           relation.relowner::bigint AS owner_oid,
           false AS is_security_definer,
           -- Only views can set security_invoker; skip parsing reloptions for every other relation.
           CASE
               WHEN relation.relkind = 'v' THEN COALESCE(
                   (
                       SELECT option_value::boolean
                       FROM pg_catalog.pg_options_to_table(relation.reloptions)
                       WHERE option_name = 'security_invoker'
                   ),
                   false
               )
               ELSE false
           END AS security_invoker,
           relation.relacl IS NULL AS has_default_acl,
           {RELATION_PRIVILEGES} AS privileges,
           {RELATION_READS_FROM} AS reads_from
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
      AND {_collected_schema("namespace")}

    UNION ALL

    SELECT 'schema'::text AS object_type,
           namespace.nspname::text AS schema_name,
           namespace.nspname::text AS object_name,
           namespace.oid::bigint AS object_oid,
           namespace.nspowner::bigint AS owner_oid,
           false AS is_security_definer,
           false AS security_invoker,
           namespace.nspacl IS NULL AS has_default_acl,
           {_json_array(_privilege_entries("namespace.nspacl"))} AS privileges,
           '[]' AS reads_from
    FROM pg_catalog.pg_namespace AS namespace
    WHERE {_collected_schema("namespace")}

    UNION ALL

    SELECT 'type'::text AS object_type,
           namespace.nspname::text AS schema_name,
           type.typname::text AS object_name,
           type.oid::bigint AS object_oid,
           type.typowner::bigint AS owner_oid,
           false AS is_security_definer,
           false AS security_invoker,
           type.typacl IS NULL AS has_default_acl,
           {_json_array(_privilege_entries("type.typacl"))} AS privileges,
           '[]' AS reads_from
    FROM pg_catalog.pg_type AS type
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = type.typnamespace
    WHERE {COLLECTED_TYPE}
      AND {_collected_schema("namespace")}

    UNION ALL

    SELECT {_routine_type(routine_kind)} AS object_type,
           namespace.nspname::text AS schema_name,
           {ROUTINE_NAME} AS object_name,
           routine.oid::bigint AS object_oid,
           routine.proowner::bigint AS owner_oid,
           routine.prosecdef AS is_security_definer,
           false AS security_invoker,
           routine.proacl IS NULL AS has_default_acl,
           {_json_array(_privilege_entries("routine.proacl"))} AS privileges,
           '[]' AS reads_from
    FROM pg_catalog.pg_proc AS routine
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = routine.pronamespace
    WHERE {routine_kind} IN ('f', 'p', 'a', 'w')
      AND {_collected_schema("namespace")}

    UNION ALL

    SELECT 'database'::text AS object_type,
           ''::text AS schema_name,
           database.datname::text AS object_name,
           database.oid::bigint AS object_oid,
           database.datdba::bigint AS owner_oid,
           false AS is_security_definer,
           false AS security_invoker,
           database.datacl IS NULL AS has_default_acl,
           {_json_array(_privilege_entries("database.datacl"))} AS privileges,
           '[]' AS reads_from
    FROM pg_catalog.pg_database AS database
    WHERE database.datname = current_database()
) AS objects
"""


# Both variants are built once, when the module loads; the collector selects one for the server version.
OBJECTS_QUERIES = {True: _objects_query(ROUTINE_KIND_PG11_PLUS), False: _objects_query(ROUTINE_KIND_PRE_PG11)}


def objects_query(*, pg11_plus: bool) -> str:
    """Select the object query for the connected server version."""
    return OBJECTS_QUERIES[pg11_plus]
