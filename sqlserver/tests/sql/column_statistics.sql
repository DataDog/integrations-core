-- The datadog.column_statistics procedure that collect_column_statistics calls, as customers install it from the setup
-- documentation in each database. The test setups load this file, so keep the documentation's copy in sync with it.
--
-- It returns only the counts in each column's statistics histogram, never the histogram's values. The Agent derives
-- the statistics from them, so changes to that logic don't need the procedure to be reinstalled.
CREATE OR ALTER PROCEDURE datadog.column_statistics @max_tables INT = 500
WITH EXECUTE AS OWNER
AS
BEGIN
    SET NOCOUNT ON;
    -- One statistics object per column: unfiltered, on the column as its leading key, the most fully sampled. Every
    -- value of a fixed-width type takes its storage size, so only variable-width columns need DBCC below.
    SELECT object_id, stats_id, stats_name, column_name, is_nullable, [rows], rows_sampled, last_updated, fixed_width,
        CAST(NULL AS FLOAT) AS avg_width
    INTO #stats
    FROM (
        SELECT st.object_id, st.stats_id, st.name AS stats_name, c.name AS column_name, c.is_nullable, sp.[rows],
            sp.rows_sampled, sp.last_updated,
            CASE WHEN TYPE_NAME(c.system_type_id) IN ('varchar', 'nvarchar', 'varbinary', 'sql_variant')
                OR c.system_type_id = 240 THEN NULL ELSE CAST(c.max_length AS FLOAT) END AS fixed_width,
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

    -- A variable-width column's average is only in the density vector, which only DBCC SHOW_STATISTICS returns.
    CREATE TABLE #density (all_density FLOAT, average_length FLOAT, columns NVARCHAR(4000));
    DECLARE @object_id INT, @stats_id INT, @table NVARCHAR(300), @stats_name SYSNAME, @column_name SYSNAME;
    DECLARE stats_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT object_id, stats_id, QUOTENAME(OBJECT_SCHEMA_NAME(object_id)) + N'.' + QUOTENAME(OBJECT_NAME(object_id)),
            stats_name, column_name
        FROM #stats
        WHERE fixed_width IS NULL;
    OPEN stats_cursor;
    FETCH NEXT FROM stats_cursor INTO @object_id, @stats_id, @table, @stats_name, @column_name;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        TRUNCATE TABLE #density;
        INSERT INTO #density
        EXEC sp_executesql N'DBCC SHOW_STATISTICS (@table, @stats_name) WITH DENSITY_VECTOR, NO_INFOMSGS',
            N'@table NVARCHAR(300), @stats_name SYSNAME', @table, @stats_name;
        UPDATE #stats SET avg_width = (SELECT TOP 1 average_length FROM #density WHERE columns = @column_name)
        WHERE object_id = @object_id AND stats_id = @stats_id;
        FETCH NEXT FROM stats_cursor INTO @object_id, @stats_id, @table, @stats_name, @column_name;
    END;
    CLOSE stats_cursor;
    DEALLOCATE stats_cursor;

    -- One row per histogram step, keeping only whether the step is the NULL step, never its value. A column whose
    -- histogram is empty, as when every value is NULL, gets a single row with no step.
    SELECT OBJECT_SCHEMA_NAME(s.object_id) AS schema_name, OBJECT_NAME(s.object_id) AS table_name, s.column_name,
        s.is_nullable, s.[rows], s.rows_sampled, DATEDIFF(SECOND, s.last_updated, SYSDATETIME()) AS stats_age,
        s.fixed_width, s.avg_width,
        CASE WHEN h.step_number IS NULL THEN NULL WHEN h.range_high_key IS NULL THEN 1 ELSE 0 END AS is_null,
        CAST(h.equal_rows AS FLOAT) AS equal_rows, CAST(h.range_rows AS FLOAT) AS range_rows,
        CAST(h.distinct_range_rows AS FLOAT) AS distinct_range_rows
    FROM #stats s
    OUTER APPLY sys.dm_db_stats_histogram(s.object_id, s.stats_id) h
    ORDER BY schema_name, table_name, s.column_name, h.step_number;
END;
GO
