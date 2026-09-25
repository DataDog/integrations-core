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


QUERY_MEMBERSHIPS_PG14_15 = """
SELECT group_role.rolname::text AS group_role_name,
       member_role.rolname::text AS member_role_name,
       grantor_role.rolname::text AS grantor_role_name,
       membership.admin_option AS admin_option,
       member_role.rolinherit AS member_can_inherit
FROM pg_catalog.pg_auth_members AS membership
JOIN pg_catalog.pg_roles AS group_role
  ON group_role.oid = membership.roleid
JOIN pg_catalog.pg_roles AS member_role
  ON member_role.oid = membership.member
JOIN pg_catalog.pg_roles AS grantor_role
  ON grantor_role.oid = membership.grantor
ORDER BY group_role_name, member_role_name, grantor_role_name
"""


QUERY_MEMBERSHIPS_PG16_PLUS = """
SELECT group_role.rolname::text AS group_role_name,
       member_role.rolname::text AS member_role_name,
       grantor_role.rolname::text AS grantor_role_name,
       membership.admin_option AS admin_option,
       membership.inherit_option AS member_can_inherit
FROM pg_catalog.pg_auth_members AS membership
JOIN pg_catalog.pg_roles AS group_role
  ON group_role.oid = membership.roleid
JOIN pg_catalog.pg_roles AS member_role
  ON member_role.oid = membership.member
JOIN pg_catalog.pg_roles AS grantor_role
  ON grantor_role.oid = membership.grantor
ORDER BY group_role_name, member_role_name, grantor_role_name
"""


def memberships_query(*, pg16_plus: bool) -> str:
    """Select the membership query for the connected server version."""
    if pg16_plus:
        return QUERY_MEMBERSHIPS_PG16_PLUS
    return QUERY_MEMBERSHIPS_PG14_15


QUERY_ROLE_SETTINGS = """
SELECT role_settings.rolname::text AS role_name,
       role_settings.database_name,
       split_part(role_settings.setting, '=', 1) AS setting_name,
       substr(
           role_settings.setting,
           strpos(role_settings.setting, '=') + 1
       ) AS setting_value
FROM (
    SELECT role.rolname,
           COALESCE(database.datname::text, '') AS database_name,
           unnest(settings.setconfig) AS setting
    FROM pg_catalog.pg_db_role_setting AS settings
    JOIN pg_catalog.pg_roles AS role
      ON role.oid = settings.setrole
    LEFT JOIN pg_catalog.pg_database AS database
      ON database.oid = settings.setdatabase
) AS role_settings
ORDER BY role_name, database_name, setting_name
"""


QUERY_DEFAULT_PRIVILEGES = """
SELECT current_database()::text AS database_name,
       owner.rolname::text AS owner_name,
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


QUERY_OBJECT_PRIVILEGES = """
SELECT privileges.database_name,
       privileges.object_type,
       privileges.schema_name,
       privileges.object_name,
       privileges.column_name,
       privileges.grantee_name,
       privileges.grantor_name,
       privileges.privilege,
       privileges.is_grantable,
       privileges.owner_name
FROM (
    SELECT current_database()::text AS database_name,
           CASE relation.relkind
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
    CROSS JOIN LATERAL pg_catalog.aclexplode(
        COALESCE(
            relation.relacl,
            pg_catalog.acldefault(
                CASE WHEN relation.relkind = 'S' THEN 's' ELSE 'r' END::"char",
                relation.relowner
            )
        )
    ) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT current_database()::text AS database_name,
           'schema'::text AS object_type,
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
    CROSS JOIN LATERAL pg_catalog.aclexplode(
        COALESCE(
            namespace.nspacl,
            pg_catalog.acldefault('n'::"char", namespace.nspowner)
        )
    ) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT current_database()::text AS database_name,
           CASE routine.prokind
               WHEN 'p' THEN 'procedure'
               WHEN 'a' THEN 'aggregate'
               ELSE 'function'
           END AS object_type,
           namespace.nspname::text AS schema_name,
           (
               routine.proname
               || '('
               || pg_catalog.pg_get_function_identity_arguments(routine.oid)
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
    CROSS JOIN LATERAL pg_catalog.aclexplode(
        COALESCE(
            routine.proacl,
            pg_catalog.acldefault('f'::"char", routine.proowner)
        )
    ) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE routine.prokind IN ('f', 'p', 'a', 'w')
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT database.datname::text AS database_name,
           'database'::text AS object_type,
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
    CROSS JOIN LATERAL pg_catalog.aclexplode(
        COALESCE(
            database.datacl,
            pg_catalog.acldefault('d'::"char", database.datdba)
        )
    ) AS acl
    LEFT JOIN pg_catalog.pg_roles AS grantee
      ON grantee.oid = acl.grantee
    LEFT JOIN pg_catalog.pg_roles AS grantor
      ON grantor.oid = acl.grantor
    WHERE database.datname = current_database()
) AS privileges
"""


QUERY_OBJECTS = """
SELECT objects.database_name,
       objects.object_type,
       objects.schema_name,
       objects.object_name,
       objects.object_oid,
       objects.owner_name,
       objects.is_security_definer,
       objects.security_invoker,
       objects.has_default_acl
FROM (
    SELECT current_database()::text AS database_name,
           CASE relation.relkind
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

    SELECT current_database()::text AS database_name,
           'schema'::text AS object_type,
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

    SELECT current_database()::text AS database_name,
           CASE routine.prokind
               WHEN 'p' THEN 'procedure'
               WHEN 'a' THEN 'aggregate'
               ELSE 'function'
           END AS object_type,
           namespace.nspname::text AS schema_name,
           (
               routine.proname
               || '('
               || pg_catalog.pg_get_function_identity_arguments(routine.oid)
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
    WHERE routine.prokind IN ('f', 'p', 'a', 'w')
      AND namespace.nspname NOT IN ('pg_catalog', 'information_schema', 'datadog')
      AND namespace.nspname NOT LIKE 'pg_toast%'
      AND namespace.nspname NOT LIKE 'pg_temp%'

    UNION ALL

    SELECT database.datname::text AS database_name,
           'database'::text AS object_type,
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


QUERY_OBJECT_DEPENDENCIES = """
SELECT DISTINCT
       current_database()::text AS database_name,
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
