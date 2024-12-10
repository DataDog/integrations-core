# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.database_metrics.xe_session_metrics import XE_RING_BUFFER

DB_QUERY = """
SELECT
    db.database_id AS id, db.name AS name, db.collation_name AS collation, dp.name AS owner
FROM
    sys.databases db LEFT JOIN sys.database_principals dp ON db.owner_sid = dp.sid
WHERE db.name IN ({});
"""

SCHEMA_QUERY = """
SELECT
    s.name AS name, s.schema_id AS id, dp.name AS owner_name
FROM
    sys.schemas AS s JOIN sys.database_principals dp ON s.principal_id = dp.principal_id
WHERE s.name NOT IN ('sys', 'information_schema')
"""

TABLES_IN_SCHEMA_QUERY = """
SELECT
    object_id AS id, name
FROM
    sys.tables
WHERE schema_id=?
"""

COLUMN_QUERY = """
SELECT
    column_name AS name, data_type, column_default, is_nullable AS nullable , table_name, ordinal_position
FROM
    information_schema.columns
WHERE
    table_name IN ({}) and table_schema='{}';
"""

PARTITIONS_QUERY = """
SELECT
    object_id AS id, COUNT(*) AS partition_count
FROM
    sys.partitions
WHERE
    object_id IN ({}) GROUP BY object_id;
"""

INDEX_QUERY = """
SELECT
    i.object_id AS id, i.name, i.type, i.is_unique, i.is_primary_key, i.is_unique_constraint,
    i.is_disabled, STRING_AGG(c.name, ',') AS column_names
FROM
    sys.indexes i JOIN sys.index_columns ic ON i.object_id = ic.object_id
    AND i.index_id = ic.index_id JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE
    i.object_id IN ({}) GROUP BY i.object_id, i.name, i.type,
    i.is_unique, i.is_primary_key, i.is_unique_constraint, i.is_disabled;
"""

INDEX_QUERY_PRE_2017 = """
SELECT
    i.object_id AS id,
    i.name,
    i.type,
    i.is_unique,
    i.is_primary_key,
    i.is_unique_constraint,
    i.is_disabled,
    STUFF((
        SELECT ',' + c.name
        FROM sys.index_columns ic
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS column_names
FROM
    sys.indexes i
WHERE
    i.object_id IN ({})
GROUP BY
    i.object_id,
    i.name,
    i.index_id,
    i.type,
    i.is_unique,
    i.is_primary_key,
    i.is_unique_constraint,
    i.is_disabled;
"""

FOREIGN_KEY_QUERY = """
SELECT
    FK.parent_object_id AS id,
    FK.name AS foreign_key_name,
    OBJECT_NAME(FK.parent_object_id) AS referencing_table,
    STRING_AGG(COL_NAME(FKC.parent_object_id, FKC.parent_column_id),',') AS referencing_column,
    OBJECT_NAME(FK.referenced_object_id) AS referenced_table,
    STRING_AGG(COL_NAME(FKC.referenced_object_id, FKC.referenced_column_id),',') AS referenced_column
FROM
    sys.foreign_keys AS FK
    JOIN sys.foreign_key_columns AS FKC ON FK.object_id = FKC.constraint_object_id
WHERE
    FK.parent_object_id IN ({})
GROUP BY
    FK.name, FK.parent_object_id, FK.referenced_object_id;
"""

FOREIGN_KEY_QUERY_PRE_2017 = """
SELECT
    FK.parent_object_id AS id,
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
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS referenced_column
FROM
    sys.foreign_keys AS FK
WHERE
    FK.parent_object_id IN ({})
GROUP BY
    FK.name,
    FK.parent_object_id,
    FK.object_id,
    FK.referenced_object_id;
"""

XE_SESSION_DATADOG = "datadog"
XE_SESSION_SYSTEM = "system_health"
XE_SESSIONS_QUERY = f"""
SELECT
    s.name AS session_name, t.target_name AS target_name
FROM
    sys.dm_xe_sessions s
JOIN
    sys.dm_xe_session_targets t
    ON s.address = t.event_session_address
WHERE
    s.name IN ('{XE_SESSION_DATADOG}', '{XE_SESSION_SYSTEM}');
"""

DEADLOCK_TIMESTAMP_ALIAS = "timestamp"
DEADLOCK_XML_ALIAS = "event_xml"


def get_deadlocks_query(convert_xml_to_str=False, xe_session_name=XE_SESSION_DATADOG, xe_target_name=XE_RING_BUFFER):
    """
    Construct the query to fetch deadlocks from the system_health extended event session
    :param convert_xml_to_str: Whether to convert the XML to a string. This option is for MSOLEDB drivers
        that can't convert XML to str
    :return: The query to fetch deadlocks
    """
    xml_expression = "xdr.query('.')"
    if convert_xml_to_str:
        xml_expression = "CAST(xdr.query('.') AS NVARCHAR(MAX))"

    if xe_target_name == XE_RING_BUFFER:
        return f"""SELECT TOP(?) xdr.value('@timestamp', 'datetime') AS [{DEADLOCK_TIMESTAMP_ALIAS}],
            {xml_expression} AS [{DEADLOCK_XML_ALIAS}]
    FROM (SELECT CAST([target_data] AS XML) AS Target_Data
                FROM sys.dm_xe_session_targets AS xt
                INNER JOIN sys.dm_xe_sessions AS xs ON xs.address = xt.event_session_address
                WHERE xs.name = N'{xe_session_name}'
                AND xt.target_name = N'{XE_RING_BUFFER}'
        ) AS XML_Data
    CROSS APPLY Target_Data.nodes('RingBufferTarget/event[@name="xml_deadlock_report"]') AS XEventData(xdr)
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
WHERE object_name like 'xml_deadlock_report'
  and CONVERT(xml, event_data).value('(event[@name="xml_deadlock_report"]/@timestamp)[1]','datetime')
    >= DATEADD(SECOND, ?, TODATETIMEOFFSET(GETDATE(), DATEPART(TZOFFSET, SYSDATETIMEOFFSET())) AT TIME ZONE 'UTC');"""
