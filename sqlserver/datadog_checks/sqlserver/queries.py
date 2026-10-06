# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.database_metrics.xe_session_metrics import XE_RING_BUFFER

# `{}` is replaced with comma-separated ODBC `?` placeholders (values bound via parameters).
DB_QUERY = """
SELECT
    db.database_id AS id, db.name AS name, db.collation_name AS collation, dp.name AS owner,
    db.compatibility_level AS compatibility_level
FROM
    sys.databases db LEFT JOIN sys.database_principals dp ON db.owner_sid = dp.sid
WHERE db.name IN ({});
"""

SCHEMA_QUERY = """
SELECT
    s.name AS schema_name, s.schema_id AS schema_id, dp.name AS owner_name
FROM
    sys.schemas AS s JOIN sys.database_principals dp ON s.principal_id = dp.principal_id
WHERE s.name NOT IN ('sys', 'information_schema')
"""

TABLES_QUERY = """
SELECT
    object_id AS table_id, name AS table_name, schema_id
FROM
    sys.tables
"""

VIEWS_QUERY = """
SELECT
    v.object_id AS view_id,
    v.name AS view_name,
    v.schema_id,
    CONVERT(varchar(33), v.create_date, 126) AS create_date,
    CONVERT(varchar(33), v.modify_date, 126) AS modify_date,
    m.definition
FROM
    sys.views v
    LEFT JOIN sys.sql_modules m ON v.object_id = m.object_id
WHERE
    v.is_ms_shipped = 0
"""

COLUMN_QUERY = """
SELECT
    c.name, t.name as data_type, coalesce(dc.definition, 'None') as "default", c.is_nullable AS nullable
FROM
    sys.columns c
    INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
    LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
WHERE c.object_id = schema_tables.table_id
"""

VIEW_COLUMN_QUERY = """
SELECT
    c.name,
    t.name AS data_type,
    coalesce(dc.definition, 'None') AS "default",
    c.is_nullable AS nullable,
    CONVERT(varchar(10), c.column_id) AS ordinal_position
FROM
    sys.columns c
    INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
    LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
WHERE c.object_id = schema_views.view_id
ORDER BY c.column_id
"""

PARTITIONS_QUERY = """
SELECT
    COUNT(*) AS partition_count
FROM
    sys.partitions
WHERE
    object_id = schema_tables.table_id
GROUP BY object_id
"""

INDEX_QUERY = """
SELECT
    i.name, i.type, i.is_unique, i.is_primary_key, i.is_unique_constraint, i.is_disabled,
    ISNULL(STRING_AGG(
        CASE
            WHEN ic.is_included_column = 0 AND ic.key_ordinal > 0 THEN
                CASE
                    WHEN ic.is_descending_key = 1 THEN CAST(c.name AS NVARCHAR(MAX)) + N' DESC'
                    ELSE CAST(c.name AS NVARCHAR(MAX))
                END
        END, ',') WITHIN GROUP (ORDER BY sk.sort_key, ic.index_column_id), N'') AS key_columns,
    ISNULL(STRING_AGG(
        CASE WHEN ic.is_included_column = 1 THEN CAST(c.name AS NVARCHAR(MAX)) END,
        ',') WITHIN GROUP (ORDER BY sk.sort_key, ic.index_column_id), N'') AS included_columns,
    STRING_AGG(CAST(c.name AS NVARCHAR(MAX)), ',')
        WITHIN GROUP (ORDER BY sk.sort_key, ic.index_column_id) AS column_names
FROM
    sys.indexes i
    JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
    JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
    CROSS APPLY (
        SELECT CASE
            WHEN ic.is_included_column = 0 AND ic.key_ordinal > 0 THEN ic.key_ordinal
            ELSE ic.index_column_id
        END AS sort_key
    ) sk
WHERE i.object_id = schema_tables.table_id
    AND i.type <> 0
GROUP BY
    i.object_id, i.index_id, i.name, i.type,
    i.is_unique, i.is_primary_key, i.is_unique_constraint, i.is_disabled
"""

# Same single catalog read as INDEX_QUERY. STRING_AGG is unavailable here, so the
# index columns are read once into XML. @k is key_ordinal and @i is index_column_id.
INDEX_QUERY_PRE_2017 = """
SELECT
    i.object_id AS id,
    i.name,
    i.type,
    i.is_unique,
    i.is_primary_key,
    i.is_unique_constraint,
    i.is_disabled,
    ISNULL(STUFF((
        SELECT ',' + col.value('(k/text())[1]', 'nvarchar(max)')
        FROM cols.x.nodes('/c') AS T(col)
        WHERE col.value('(k/text())[1]', 'nvarchar(max)') IS NOT NULL
        ORDER BY col.value('@k', 'int')
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, ''), '') AS key_columns,
    ISNULL(STUFF((
        SELECT ',' + col.value('(inc/text())[1]', 'nvarchar(max)')
        FROM cols.x.nodes('/c') AS T(col)
        WHERE col.value('(inc/text())[1]', 'nvarchar(max)') IS NOT NULL
        ORDER BY col.value('@i', 'int')
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, ''), '') AS included_columns,
    STUFF((
        SELECT ',' + col.value('(n/text())[1]', 'nvarchar(max)')
        FROM cols.x.nodes('/c') AS T(col)
        ORDER BY col.value('@i', 'int')
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS column_names
FROM
    sys.indexes i
    CROSS APPLY (
        SELECT ISNULL(raw.x, CAST('<r/>' AS XML)) AS x
        FROM (
            SELECT (
                SELECT
                    ic.key_ordinal AS [@k],
                    ic.index_column_id AS [@i],
                    CASE
                        WHEN ic.is_included_column = 0 AND ic.key_ordinal > 0 THEN
                            CASE WHEN ic.is_descending_key = 1 THEN c.name + ' DESC' ELSE c.name END
                    END AS k,
                    CASE WHEN ic.is_included_column = 1 THEN c.name END AS inc,
                    c.name AS n
                FROM sys.index_columns ic
                JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                FOR XML PATH('c'), TYPE
            ) AS x
        ) raw
    ) AS cols
WHERE i.object_id = schema_tables.table_id
    AND i.type <> 0
"""

FOREIGN_KEY_QUERY = """
SELECT
    FK.name AS foreign_key_name,
    OBJECT_NAME(FK.parent_object_id) AS referencing_table,
    STRING_AGG(COL_NAME(FKC.parent_object_id, FKC.parent_column_id),',') AS referencing_column,
    OBJECT_NAME(FK.referenced_object_id) AS referenced_table,
    STRING_AGG(COL_NAME(FKC.referenced_object_id, FKC.referenced_column_id),',') AS referenced_column,
    FK.delete_referential_action_desc AS delete_action,
    FK.update_referential_action_desc AS update_action
FROM
    sys.foreign_keys AS FK
    JOIN sys.foreign_key_columns AS FKC ON FK.object_id = FKC.constraint_object_id
WHERE FK.parent_object_id = schema_tables.table_id
GROUP BY
    FK.name,
    FK.parent_object_id,
    FK.referenced_object_id,
    FK.delete_referential_action_desc,
    FK.update_referential_action_desc
"""

FOREIGN_KEY_QUERY_PRE_2017 = """
SELECT
    FK.parent_object_id AS table_id,
    FK.name AS foreign_key_name,
    OBJECT_NAME(FK.parent_object_id) AS referencing_table,
    STUFF((
        SELECT ',' + COL_NAME(FKC.parent_object_id, FKC.parent_column_id)
        FROM sys.foreign_key_columns AS FKC
        WHERE FKC.constraint_object_id = FK.object_id
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS referencing_column,
    OBJECT_NAME(FK.referenced_object_id) AS referenced_table,
    STUFF((
        SELECT ',' + COL_NAME(FKC.referenced_object_id, FKC.referenced_column_id)
        FROM sys.foreign_key_columns AS FKC
        WHERE FKC.constraint_object_id = FK.object_id
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS referenced_column,
    FK.delete_referential_action_desc AS delete_action,
    FK.update_referential_action_desc AS update_action
FROM
    sys.foreign_keys AS FK
WHERE FK.parent_object_id = schema_tables.table_id
GROUP BY
    FK.name,
    FK.object_id,
    FK.parent_object_id,
    FK.referenced_object_id,
    FK.delete_referential_action_desc,
    FK.update_referential_action_desc
"""

DEFAULT_DM_XE_TARGETS = "sys.dm_xe_session_targets"
DEFAULT_DM_XE_SESSIONS = "sys.dm_xe_sessions"
XE_SESSION_DATADOG = "datadog"
XE_SESSION_SYSTEM = "system_health"


def get_xe_sessions_query(dm_xe_targets=DEFAULT_DM_XE_TARGETS, dm_xe_sessions=DEFAULT_DM_XE_SESSIONS):
    return f"""
SELECT
    s.name AS session_name, t.target_name AS target_name
FROM
    {dm_xe_sessions} s
JOIN
    {dm_xe_targets} t
    ON s.address = t.event_session_address
WHERE
    s.name IN ('{XE_SESSION_DATADOG}', '{XE_SESSION_SYSTEM}');
"""


DEADLOCK_TIMESTAMP_ALIAS = "timestamp"
DEADLOCK_XML_ALIAS = "event_xml"


def get_deadlocks_query(
    convert_xml_to_str=False,
    xe_session_name=XE_SESSION_DATADOG,
    xe_target_name=XE_RING_BUFFER,
    dm_xe_targets=DEFAULT_DM_XE_TARGETS,
    dm_xe_sessions=DEFAULT_DM_XE_SESSIONS,
    level="",
):
    """
    Construct the query to fetch deadlocks from the system_health extended event session
    :params:
        convert_xml_to_str: Whether to convert the XML to a string. This option is for MSOLEDB drivers
            that can't convert XML to str
        xe_session_name: The name of the extended event session to query
        xe_target_name: The name of the extended event target to query
        dm_xe_targets: The name of the DMV to query for extended event targets
        dm_xe_sessions: The name of the DMV to query for extended event sessions
        level: 'database_' for Azure database, '' for all other versions
    :return: The query to fetch deadlocks
    """
    xml_expression = "xdr.query('.')"
    if convert_xml_to_str:
        xml_expression = "CAST(xdr.query('.') AS NVARCHAR(MAX))"

    if xe_target_name == XE_RING_BUFFER:
        return f"""SELECT TOP(?) xdr.value('@timestamp', 'datetime') AS [{DEADLOCK_TIMESTAMP_ALIAS}],
            {xml_expression} AS [{DEADLOCK_XML_ALIAS}]
    FROM (SELECT CAST([target_data] AS XML) AS Target_Data
                FROM {dm_xe_targets} AS xt
                INNER JOIN {dm_xe_sessions} AS xs ON xs.address = xt.event_session_address
                WHERE xs.name = N'{xe_session_name}'
                AND xt.target_name = N'{XE_RING_BUFFER}'
        ) AS XML_Data
    CROSS APPLY Target_Data.nodes('RingBufferTarget/event[@name="{level}xml_deadlock_report"]') AS XEventData(xdr)
    WHERE xdr.value('@timestamp', 'datetime')
        >= DATEADD(SECOND, ?, TODATETIMEOFFSET(GETDATE(), DATEPART(TZOFFSET, SYSDATETIMEOFFSET())) AT TIME ZONE 'UTC')
    ;"""

    return f"""SELECT TOP(?)
event_data AS [{DEADLOCK_XML_ALIAS}],
CONVERT(xml, event_data).value('(event[@name="xml_deadlock_report"]/@timestamp)[1]','datetime')
    AS [{DEADLOCK_TIMESTAMP_ALIAS}]
FROM
sys.fn_xe_file_target_read_file
('system_health*.xel', null, null, null)
WHERE object_name = 'xml_deadlock_report'
  and CONVERT(xml, event_data).value('(event[@name="xml_deadlock_report"]/@timestamp)[1]','datetime')
    >= DATEADD(SECOND, ?, TODATETIMEOFFSET(GETDATE(), DATEPART(TZOFFSET, SYSDATETIMEOFFSET())) AT TIME ZONE 'UTC');"""
