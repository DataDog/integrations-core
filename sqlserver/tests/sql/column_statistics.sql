-- The datadog.column_statistics procedure that collect_column_statistics calls, as customers install it from the setup
-- documentation in each database. The test setups load this file, so keep the documentation's copy in sync with it.
--
-- It returns each column's statistics as SQL Server reports them, with the same names, but only the counts in its
-- histogram, never the histogram's values. If the columns it returns ever change, the Agent warns that the installed
-- procedure is outdated.
CREATE OR ALTER PROCEDURE datadog.column_statistics @max_tables INT = 500
WITH EXECUTE AS OWNER
AS
BEGIN
    SET NOCOUNT ON;
    -- One statistics object per column: unfiltered, on the column as its leading key, the most fully sampled. A column
    -- is unique when an unfiltered unique index or primary key has it as its only key, which a sampled histogram can't
    -- tell.
    SELECT object_id, stats_id, stats_name, auto_created, user_created, column_name, type_name, max_length, is_nullable,
        is_unique, last_updated, [rows], rows_sampled, steps, modification_counter, CAST(NULL AS FLOAT) AS average_length
    INTO #stats
    FROM (
        SELECT st.object_id, st.stats_id, st.name AS stats_name, st.auto_created, st.user_created, c.name AS column_name,
            -- An alias type's base type, but a CLR type's own name: CLR types share system_type_id 240, which has none.
            TYPE_NAME(CASE WHEN c.system_type_id = 240 THEN c.user_type_id ELSE c.system_type_id END) AS type_name,
            c.max_length, c.is_nullable,
            CAST(CASE WHEN EXISTS (
                SELECT 1
                FROM sys.indexes i
                JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                    AND ic.key_ordinal = 1
                WHERE i.object_id = c.object_id AND ic.column_id = c.column_id AND i.is_unique = 1
                    AND i.has_filter = 0 AND INDEXKEY_PROPERTY(i.object_id, i.index_id, 2, 'ColumnId') IS NULL
            ) THEN 1 ELSE 0 END AS BIT) AS is_unique,
            -- As ISO 8601 text in UTC, since the server's time zone is unknown to the reader, and older drivers such as
            -- SQLOLEDB return datetime2 values as text in their own format. It's converted with the server's current
            -- offset, so statistics updated before a daylight saving change are an hour off. Style 126 leaves out the
            -- fraction of a second when it's zero.
            CONVERT(VARCHAR(27), DATEADD(MINUTE, DATEPART(TZOFFSET, SYSDATETIMEOFFSET()) * -1, sp.last_updated), 126)
                + 'Z' AS last_updated,
            sp.[rows], sp.rows_sampled, sp.steps, sp.modification_counter,
            ROW_NUMBER() OVER (PARTITION BY st.object_id, sc.column_id ORDER BY sp.rows_sampled DESC, sp.last_updated DESC) AS rn
        FROM (SELECT TOP (@max_tables) object_id FROM sys.tables WHERE is_ms_shipped = 0 ORDER BY SCHEMA_NAME(schema_id), name) t
        JOIN sys.stats st ON st.object_id = t.object_id AND st.has_filter = 0
        JOIN sys.stats_columns sc ON sc.object_id = st.object_id AND sc.stats_id = st.stats_id AND sc.stats_column_id = 1
        JOIN sys.columns c ON c.object_id = sc.object_id AND c.column_id = sc.column_id
        CROSS APPLY sys.dm_db_stats_properties(st.object_id, st.stats_id) sp
        WHERE sp.[rows] > 0
    ) s
    WHERE rn = 1;
    CREATE CLUSTERED INDEX ix_stats ON #stats (object_id, stats_id);

    -- A variable-width column's average length is only in the density vector, which only DBCC SHOW_STATISTICS returns.
    -- Every value of a fixed-width type takes max_length, so those skip DBCC.
    CREATE TABLE #density (all_density FLOAT, average_length FLOAT, columns NVARCHAR(4000));
    DECLARE @object_id INT, @stats_id INT, @table NVARCHAR(300), @stats_name SYSNAME, @column_name SYSNAME;
    DECLARE stats_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT object_id, stats_id, QUOTENAME(OBJECT_SCHEMA_NAME(object_id)) + N'.' + QUOTENAME(OBJECT_NAME(object_id)),
            stats_name, column_name
        FROM #stats
        WHERE type_name IN ('varchar', 'nvarchar', 'varbinary', 'sql_variant', 'hierarchyid', 'geometry', 'geography');
    OPEN stats_cursor;
    FETCH NEXT FROM stats_cursor INTO @object_id, @stats_id, @table, @stats_name, @column_name;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        -- Statistics can be dropped since they were listed, as auto-created ones are. DBCC's error for them would fail
        -- the whole procedure, and TRY...CATCH doesn't catch it inside INSERT...EXEC.
        IF EXISTS (SELECT 1 FROM sys.stats WHERE object_id = @object_id AND stats_id = @stats_id)
        BEGIN
            TRUNCATE TABLE #density;
            INSERT INTO #density
            EXEC sp_executesql N'DBCC SHOW_STATISTICS (@table, @stats_name) WITH DENSITY_VECTOR, NO_INFOMSGS',
                N'@table NVARCHAR(300), @stats_name SYSNAME', @table, @stats_name;
            UPDATE #stats SET average_length = (SELECT TOP 1 average_length FROM #density WHERE columns = @column_name)
            WHERE object_id = @object_id AND stats_id = @stats_id;
        END;
        FETCH NEXT FROM stats_cursor INTO @object_id, @stats_id, @table, @stats_name, @column_name;
    END;
    CLOSE stats_cursor;
    DEALLOCATE stats_cursor;

    -- One row per column. Its histogram steps are packed in step_number order as
    -- range_high_key_is_null:equal_rows:range_rows:distinct_range_rows:average_range_rows, keeping only whether a
    -- step's range_high_key is NULL, never its value. A column whose histogram is empty, as when every value is NULL,
    -- has no steps.
    SELECT OBJECT_SCHEMA_NAME(s.object_id) AS schema_name, OBJECT_NAME(s.object_id) AS table_name, s.column_name,
        s.stats_name, s.auto_created, s.user_created, s.type_name, s.max_length, s.is_nullable, s.is_unique,
        s.last_updated, s.[rows], s.rows_sampled, s.steps, s.modification_counter, s.average_length, h.histogram
    FROM #stats s
    OUTER APPLY (
        -- STRING_AGG stops at 8000 bytes unless its input is VARCHAR(MAX); 201 steps can exceed that.
        SELECT STRING_AGG(CAST(CONCAT(CASE WHEN hh.range_high_key IS NULL THEN 1 ELSE 0 END, ':',
                CAST(hh.equal_rows AS DECIMAL(19, 2)), ':', CAST(hh.range_rows AS DECIMAL(19, 2)), ':',
                CAST(hh.distinct_range_rows AS DECIMAL(19, 2)), ':', CAST(hh.average_range_rows AS DECIMAL(19, 4)))
                AS VARCHAR(MAX)), ',') WITHIN GROUP (ORDER BY hh.step_number) AS histogram
        FROM sys.dm_db_stats_histogram(s.object_id, s.stats_id) hh
    ) h
    ORDER BY schema_name, table_name, s.column_name;
END;
GO
