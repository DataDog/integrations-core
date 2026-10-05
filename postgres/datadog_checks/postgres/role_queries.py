# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

QUERY_LIST_DATABASES = """
SELECT d.datname::text AS database_name
FROM pg_catalog.pg_database AS d
WHERE d.datallowconn
  AND NOT d.datistemplate
  AND {database_filter}
ORDER BY database_name
"""


def list_databases_query(database_filter: str = "TRUE") -> str:
    """Build the database discovery query with a collector-generated filter."""
    return QUERY_LIST_DATABASES.format(database_filter=database_filter)


QUERY_ROLES = """
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
       pg_catalog.to_json(r.rolvaliduntil) AS valid_until
FROM pg_catalog.pg_roles AS r
ORDER BY role_name
"""


# Before PostgreSQL 16, dropping a role leaves memberships it granted pointing at its OID, so the grantor is
# reported by OID rather than dropping a membership that is still in effect.
QUERY_MEMBERSHIPS_PG14_15 = """
SELECT group_role.rolname::text AS group_role_name,
       member_role.rolname::text AS member_role_name,
       COALESCE(grantor_role.rolname::text, membership.grantor::text) AS grantor_role_name,
       membership.admin_option AS admin_option,
       member_role.rolinherit AS member_can_inherit
FROM pg_catalog.pg_auth_members AS membership
JOIN pg_catalog.pg_roles AS group_role
  ON group_role.oid = membership.roleid
JOIN pg_catalog.pg_roles AS member_role
  ON member_role.oid = membership.member
LEFT JOIN pg_catalog.pg_roles AS grantor_role
  ON grantor_role.oid = membership.grantor
ORDER BY group_role_name, member_role_name, grantor_role_name
"""


QUERY_MEMBERSHIPS_PG16_PLUS = """
SELECT group_role.rolname::text AS group_role_name,
       member_role.rolname::text AS member_role_name,
       COALESCE(grantor_role.rolname::text, membership.grantor::text) AS grantor_role_name,
       membership.admin_option AS admin_option,
       membership.inherit_option AS member_can_inherit
FROM pg_catalog.pg_auth_members AS membership
JOIN pg_catalog.pg_roles AS group_role
  ON group_role.oid = membership.roleid
JOIN pg_catalog.pg_roles AS member_role
  ON member_role.oid = membership.member
LEFT JOIN pg_catalog.pg_roles AS grantor_role
  ON grantor_role.oid = membership.grantor
ORDER BY group_role_name, member_role_name, grantor_role_name
"""


def memberships_query(*, pg16_plus: bool) -> str:
    """Select the membership query for the connected server version."""
    if pg16_plus:
        return QUERY_MEMBERSHIPS_PG16_PLUS
    return QUERY_MEMBERSHIPS_PG14_15


# Built-in settings have no dot in their name. Every dotted setting belongs to an extension or application, and
# those can hold secrets such as `pgrst.jwt_secret` or `anon.salt`, whether or not a loaded module registers them.
# Their values are kept only for extensions known to hold no secrets; other names are reported as redacted.
ROLE_SETTING_VALUE_PREFIXES = ("auto_explain", "pg_hint_plan", "pg_stat_statements", "pgaudit", "plpgsql")

# Takes the allowed prefixes as its only parameter. Prefixes are matched case-insensitively because custom setting
# names keep the case they were written in.
QUERY_ROLE_SETTINGS = """
SELECT role_settings.rolname::text AS role_name,
       role_settings.database_name,
       role_settings.setting_name,
       CASE WHEN role_settings.is_value_collected THEN role_settings.setting_value END AS setting_value,
       NOT role_settings.is_value_collected AS is_value_redacted
FROM (
    SELECT role.rolname,
           COALESCE(database.datname::text, '') AS database_name,
           parsed.setting_name,
           parsed.setting_value,
           strpos(parsed.setting_name, '.') = 0
               OR lower(split_part(parsed.setting_name, '.', 1)) = ANY(%s) AS is_value_collected
    FROM pg_catalog.pg_db_role_setting AS settings
    CROSS JOIN LATERAL unnest(settings.setconfig) AS setting
    CROSS JOIN LATERAL (
        SELECT split_part(setting, '=', 1) AS setting_name,
               substr(setting, strpos(setting, '=') + 1) AS setting_value
    ) AS parsed
    JOIN pg_catalog.pg_roles AS role
      ON role.oid = settings.setrole
    LEFT JOIN pg_catalog.pg_database AS database
      ON database.oid = settings.setdatabase
) AS role_settings
ORDER BY role_name, database_name, setting_name
"""


QUERY_DEFAULT_PRIVILEGES = """
SELECT owner.rolname::text AS owner_name,
       COALESCE(namespace.nspname::text, '') AS schema_name,
       CASE default_acl.defaclobjtype
           WHEN 'r' THEN 'table'
           WHEN 'S' THEN 'sequence'
           WHEN 'f' THEN 'function'
           WHEN 'T' THEN 'type'
           WHEN 'n' THEN 'schema'
       END AS object_type,
       CASE
           WHEN acl.grantee = 0 THEN 'PUBLIC'
           ELSE COALESCE(grantee.rolname::text, acl.grantee::text)
       END AS grantee_name,
       COALESCE(grantor.rolname::text, acl.grantor::text) AS grantor_name,
       acl.privilege_type::text AS privilege,
       acl.is_grantable AS is_grantable
FROM pg_catalog.pg_default_acl AS default_acl
JOIN pg_catalog.pg_roles AS owner
  ON owner.oid = default_acl.defaclrole
LEFT JOIN pg_catalog.pg_namespace AS namespace
  ON namespace.oid = default_acl.defaclnamespace
CROSS JOIN LATERAL pg_catalog.aclexplode(default_acl.defaclacl) AS acl
LEFT JOIN pg_catalog.pg_roles AS grantee
  ON grantee.oid = acl.grantee
LEFT JOIN pg_catalog.pg_roles AS grantor
  ON grantor.oid = acl.grantor
WHERE default_acl.defaclobjtype IN ('r', 'S', 'f', 'T', 'n')
  AND (
      default_acl.defaclnamespace = 0
      OR (
          namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
          AND namespace.nspname NOT LIKE 'pg_toast%'
          AND namespace.nspname NOT LIKE 'pg_temp%'
      )
  )
"""


# Only explicitly stored ACLs are collected. An object with a NULL ACL has the compiled-in default privileges for
# its type and owner; it is reported in `objects` with `has_default_acl` so the backend can resolve them, rather
# than shipping the same owner and PUBLIC rows for every untouched object.
# Column grants are stored only on columns granted individually: table-level grants never populate `attacl`, and
# columns have no default privileges. A column row adds access on top of the relation's own privileges.
QUERY_OBJECT_PRIVILEGES = """
SELECT privileges.object_type,
       privileges.schema_name,
       privileges.object_name,
       privileges.column_name,
       privileges.grantee_name,
       privileges.grantor_name,
       privileges.privilege,
       privileges.is_grantable,
       privileges.owner_name
FROM (
    SELECT CASE relation.relkind
               WHEN 'r' THEN 'table'
               WHEN 'p' THEN 'partitioned_table'
               WHEN 'v' THEN 'view'
               WHEN 'm' THEN 'materialized_view'
               WHEN 'f' THEN 'foreign_table'
               WHEN 'S' THEN 'sequence'
           END AS object_type,
           namespace.nspname::text AS schema_name,
           relation.relname::text AS object_name,
           ''::text AS column_name,
           CASE
               WHEN acl.grantee = 0 THEN 'PUBLIC'
               ELSE COALESCE(grantee.rolname::text, acl.grantee::text)
           END AS grantee_name,
           COALESCE(grantor.rolname::text, acl.grantor::text) AS grantor_name,
           acl.privilege_type::text AS privilege,
           acl.is_grantable AS is_grantable,
           owner.rolname::text AS owner_name
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = relation.relowner
    CROSS JOIN LATERAL pg_catalog.aclexplode(relation.relacl) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT CASE relation.relkind
               WHEN 'r' THEN 'table'
               WHEN 'p' THEN 'partitioned_table'
               WHEN 'v' THEN 'view'
               WHEN 'm' THEN 'materialized_view'
               WHEN 'f' THEN 'foreign_table'
           END AS object_type,
           namespace.nspname::text AS schema_name,
           relation.relname::text AS object_name,
           attribute.attname::text AS column_name,
           CASE
               WHEN acl.grantee = 0 THEN 'PUBLIC'
               ELSE COALESCE(grantee.rolname::text, acl.grantee::text)
           END AS grantee_name,
           COALESCE(grantor.rolname::text, acl.grantor::text) AS grantor_name,
           acl.privilege_type::text AS privilege,
           acl.is_grantable AS is_grantable,
           owner.rolname::text AS owner_name
    FROM pg_catalog.pg_attribute AS attribute
    JOIN pg_catalog.pg_class AS relation
      ON relation.oid = attribute.attrelid
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = relation.relowner
    CROSS JOIN LATERAL pg_catalog.aclexplode(attribute.attacl) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f')
      AND attribute.attnum > 0
      AND NOT attribute.attisdropped
      AND attribute.attacl IS NOT NULL
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT 'schema'::text AS object_type,
           namespace.nspname::text AS schema_name,
           namespace.nspname::text AS object_name,
           ''::text AS column_name,
           CASE
               WHEN acl.grantee = 0 THEN 'PUBLIC'
               ELSE COALESCE(grantee.rolname::text, acl.grantee::text)
           END AS grantee_name,
           COALESCE(grantor.rolname::text, acl.grantor::text) AS grantor_name,
           acl.privilege_type::text AS privilege,
           acl.is_grantable AS is_grantable,
           owner.rolname::text AS owner_name
    FROM pg_catalog.pg_namespace AS namespace
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = namespace.nspowner
    CROSS JOIN LATERAL pg_catalog.aclexplode(namespace.nspacl) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT CASE {routine_kind}
               WHEN 'p' THEN 'procedure'
               WHEN 'a' THEN 'aggregate'
               ELSE 'function'
           END AS object_type,
           namespace.nspname::text AS schema_name,
           (
               routine.proname
               || '('
               || pg_catalog.oidvectortypes(routine.proargtypes)
               || ')'
           )::text AS object_name,
           ''::text AS column_name,
           CASE
               WHEN acl.grantee = 0 THEN 'PUBLIC'
               ELSE COALESCE(grantee.rolname::text, acl.grantee::text)
           END AS grantee_name,
           COALESCE(grantor.rolname::text, acl.grantor::text) AS grantor_name,
           acl.privilege_type::text AS privilege,
           acl.is_grantable AS is_grantable,
           owner.rolname::text AS owner_name
    FROM pg_catalog.pg_proc AS routine
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = routine.pronamespace
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = routine.proowner
    CROSS JOIN LATERAL pg_catalog.aclexplode(routine.proacl) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE {routine_kind} IN ('f', 'p', 'a', 'w')
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT 'database'::text AS object_type,
           ''::text AS schema_name,
           database.datname::text AS object_name,
           ''::text AS column_name,
           CASE
               WHEN acl.grantee = 0 THEN 'PUBLIC'
               ELSE COALESCE(grantee.rolname::text, acl.grantee::text)
           END AS grantee_name,
           COALESCE(grantor.rolname::text, acl.grantor::text) AS grantor_name,
           acl.privilege_type::text AS privilege,
           acl.is_grantable AS is_grantable,
           owner.rolname::text AS owner_name
    FROM pg_catalog.pg_database AS database
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = database.datdba
    CROSS JOIN LATERAL pg_catalog.aclexplode(database.datacl) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE database.datname = current_database()
) AS privileges
"""


QUERY_OBJECTS = """
SELECT objects.object_type,
       objects.schema_name,
       objects.object_name,
       objects.object_oid,
       objects.owner_name,
       objects.is_security_definer,
       objects.security_invoker,
       objects.has_default_acl
FROM (
    SELECT CASE relation.relkind
               WHEN 'r' THEN 'table'
               WHEN 'p' THEN 'partitioned_table'
               WHEN 'v' THEN 'view'
               WHEN 'm' THEN 'materialized_view'
               WHEN 'f' THEN 'foreign_table'
               WHEN 'S' THEN 'sequence'
           END AS object_type,
           namespace.nspname::text AS schema_name,
           relation.relname::text AS object_name,
           relation.oid::bigint AS object_oid,
           owner.rolname::text AS owner_name,
           false AS is_security_definer,
           COALESCE(
               (
                   SELECT option_value::boolean
                   FROM pg_catalog.pg_options_to_table(relation.reloptions)
                   WHERE option_name = 'security_invoker'
               ),
               false
           ) AS security_invoker,
           relation.relacl IS NULL AS has_default_acl
    FROM pg_catalog.pg_class AS relation
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = relation.relowner
    WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT 'schema'::text AS object_type,
           namespace.nspname::text AS schema_name,
           namespace.nspname::text AS object_name,
           namespace.oid::bigint AS object_oid,
           owner.rolname::text AS owner_name,
           false AS is_security_definer,
           false AS security_invoker,
           namespace.nspacl IS NULL AS has_default_acl
    FROM pg_catalog.pg_namespace AS namespace
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = namespace.nspowner
    WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT CASE {routine_kind}
               WHEN 'p' THEN 'procedure'
               WHEN 'a' THEN 'aggregate'
               ELSE 'function'
           END AS object_type,
           namespace.nspname::text AS schema_name,
           (
               routine.proname
               || '('
               || pg_catalog.oidvectortypes(routine.proargtypes)
               || ')'
           )::text AS object_name,
           routine.oid::bigint AS object_oid,
           owner.rolname::text AS owner_name,
           routine.prosecdef AS is_security_definer,
           false AS security_invoker,
           routine.proacl IS NULL AS has_default_acl
    FROM pg_catalog.pg_proc AS routine
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = routine.pronamespace
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = routine.proowner
    WHERE {routine_kind} IN ('f', 'p', 'a', 'w')
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT 'database'::text AS object_type,
           ''::text AS schema_name,
           database.datname::text AS object_name,
           database.oid::bigint AS object_oid,
           owner.rolname::text AS owner_name,
           false AS is_security_definer,
           false AS security_invoker,
           database.datacl IS NULL AS has_default_acl
    FROM pg_catalog.pg_database AS database
    JOIN pg_catalog.pg_roles AS owner
      ON owner.oid = database.datdba
    WHERE database.datname = current_database()
) AS objects
"""


# PostgreSQL 11 added procedures and replaced proisagg and proiswindow with prokind. Earlier versions derive the
# same kind codes, so routine branches report the same object types on every version.
ROUTINE_KIND_PG11_PLUS = "routine.prokind"
ROUTINE_KIND_PRE_PG11 = "(CASE WHEN routine.proisagg THEN 'a' WHEN routine.proiswindow THEN 'w' ELSE 'f' END)"


def _routine_kind(pg11_plus: bool) -> str:
    return ROUTINE_KIND_PG11_PLUS if pg11_plus else ROUTINE_KIND_PRE_PG11


def object_privileges_query(*, pg11_plus: bool) -> str:
    """Select the object privilege query for the connected server version."""
    return QUERY_OBJECT_PRIVILEGES.format(routine_kind=_routine_kind(pg11_plus))


def objects_query(*, pg11_plus: bool) -> str:
    """Select the object query for the connected server version."""
    return QUERY_OBJECTS.format(routine_kind=_routine_kind(pg11_plus))


QUERY_OBJECT_DEPENDENCIES = """
SELECT DISTINCT
       CASE dependent.relkind
           WHEN 'v' THEN 'view'
           WHEN 'm' THEN 'materialized_view'
       END AS dependent_object_type,
       dependent_namespace.nspname::text AS dependent_schema_name,
       dependent.relname::text AS dependent_object_name,
       CASE referenced.relkind
           WHEN 'r' THEN 'table'
           WHEN 'p' THEN 'partitioned_table'
           WHEN 'v' THEN 'view'
           WHEN 'm' THEN 'materialized_view'
           WHEN 'f' THEN 'foreign_table'
           WHEN 'S' THEN 'sequence'
       END AS referenced_object_type,
       referenced_namespace.nspname::text AS referenced_schema_name,
       referenced.relname::text AS referenced_object_name
FROM pg_catalog.pg_rewrite AS rewrite
JOIN pg_catalog.pg_class AS dependent
  ON dependent.oid = rewrite.ev_class
JOIN pg_catalog.pg_namespace AS dependent_namespace
  ON dependent_namespace.oid = dependent.relnamespace
JOIN pg_catalog.pg_depend AS dependency
  ON dependency.objid = rewrite.oid
 AND dependency.classid = 'pg_catalog.pg_rewrite'::pg_catalog.regclass
 AND dependency.refclassid = 'pg_catalog.pg_class'::pg_catalog.regclass
JOIN pg_catalog.pg_class AS referenced
  ON referenced.oid = dependency.refobjid
JOIN pg_catalog.pg_namespace AS referenced_namespace
  ON referenced_namespace.oid = referenced.relnamespace
WHERE dependent.relkind IN ('v', 'm')
  AND dependency.deptype = 'n'
  AND referenced.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
  AND referenced.oid <> dependent.oid
  AND dependent_namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
  AND dependent_namespace.nspname NOT LIKE 'pg_toast%'
  AND dependent_namespace.nspname NOT LIKE 'pg_temp%'
  AND referenced_namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
  AND referenced_namespace.nspname NOT LIKE 'pg_toast%'
  AND referenced_namespace.nspname NOT LIKE 'pg_temp%'
"""
