------------------------------ COMMON SETUP ------------------------------
ALTER login sa ENABLE;
GO
ALTER login sa WITH PASSWORD = 'Password123';
GO

-- datadog user
CREATE LOGIN datadog WITH PASSWORD = 'Password12!';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
GRANT VIEW ANY DEFINITION to datadog;


-- test users
CREATE LOGIN bob WITH PASSWORD = 'Password12!';
CREATE USER bob FOR LOGIN bob;
CREATE LOGIN fred WITH PASSWORD = 'Password12!';
CREATE USER fred FOR LOGIN fred;
GO

-- note that we deliberately don't grant "CONNECT ANY DATABASE" to the agent user here because that
-- permission is not supported in SQL Server 2012. This is OK for the integration tests because in
-- the tests instead we explicitly create the datadog user in each database as a workaround
USE model;
GO
CREATE USER datadog FOR LOGIN datadog;
GO
USE msdb;
GO
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT to datadog;
GO

-- Create test database for integration schema tests
CREATE DATABASE datadog_test_schemas;
GO
USE datadog_test_schemas;
GO

CREATE SCHEMA test_schema;
GO

-- Create the partition function
CREATE PARTITION FUNCTION CityPartitionFunction (INT)
AS RANGE LEFT FOR VALUES (100, 200, 300); -- Define your partition boundaries here

-- Create the partition scheme
CREATE PARTITION SCHEME CityPartitionScheme
AS PARTITION CityPartitionFunction ALL TO ([PRIMARY]); -- Assign partitions to filegroups

-- Create the partitioned table
CREATE TABLE datadog_test_schemas.test_schema.cities (
    id INT NOT NULL DEFAULT 0,
    name VARCHAR(255),
    population INT NOT NULL DEFAULT 0,
    CONSTRAINT PK_Cities PRIMARY KEY (id)
) ON CityPartitionScheme(id); -- Assign the partition scheme to the table

-- Create indexes
CREATE INDEX two_columns_index ON datadog_test_schemas.test_schema.cities (id, name);
CREATE INDEX single_column_index ON datadog_test_schemas.test_schema.cities (population);

INSERT INTO datadog_test_schemas.test_schema.cities  VALUES (1, 'yey', 100), (2, 'bar', 200);
GO

-- Create table with a foreign key
CREATE TABLE datadog_test_schemas.test_schema.landmarks (name varchar(255), city_id int DEFAULT 0);
GO
ALTER TABLE datadog_test_schemas.test_schema.landmarks ADD CONSTRAINT FK_CityId FOREIGN KEY (city_id)
REFERENCES datadog_test_schemas.test_schema.cities(id)
ON DELETE SET NULL;
GO

-- Create table with unique constraint
CREATE TABLE datadog_test_schemas.test_schema.Restaurants (
    RestaurantName VARCHAR(255),
    District VARCHAR(100),
    Cuisine VARCHAR(100),
    CONSTRAINT UC_RestaurantNameDistrict UNIQUE (RestaurantName, District)
);
GO

-- Create table with a foreign key on two columns
CREATE TABLE datadog_test_schemas.test_schema.RestaurantReviews (
    RestaurantName VARCHAR(255),
    District VARCHAR(100),
    Review VARCHAR(MAX),
    CONSTRAINT FK_RestaurantNameDistrict FOREIGN KEY (RestaurantName, District)
        REFERENCES datadog_test_schemas.test_schema.Restaurants(RestaurantName, District)
        ON DELETE CASCADE
        ON UPDATE SET NULL
);
GO

-- Both indexes contain a, c, and e. key_columns and included_columns keep the key and INCLUDE list apart.
CREATE TABLE datadog_test_schemas.test_schema.index_coverage (
    a INT,
    c INT,
    e INT
);
CREATE INDEX ix_include ON datadog_test_schemas.test_schema.index_coverage (c) INCLUDE (a, e);
CREATE INDEX ix_prefix ON datadog_test_schemas.test_schema.index_coverage (c, a) INCLUDE (e);
GO

-- ix_filtered covers only rows where e is not null.
CREATE INDEX ix_filtered ON datadog_test_schemas.test_schema.index_coverage (a) WHERE e IS NOT NULL;
GO

-- Clustered (b, a) is not table column order, and ix_desc keeps the DESC suffix.
CREATE TABLE datadog_test_schemas.test_schema.key_order (
    a INT,
    b INT,
    c INT,
    CONSTRAINT pk_key_order PRIMARY KEY CLUSTERED (b, a)
);
CREATE INDEX ix_desc ON datadog_test_schemas.test_schema.key_order (c DESC, a);
GO

-- Create second test database for integration schema tests
CREATE DATABASE datadog_test_schemas_second;
GO
USE datadog_test_schemas_second;
-- This table is pronounced "things" except we've replaced "th" with the greek lower case "theta" to ensure we
-- correctly support unicode throughout the integration.
CREATE TABLE datadog_test_schemas_second.dbo.ϑings (id int DEFAULT 0, name varchar(255));
INSERT INTO datadog_test_schemas_second.dbo.ϑings VALUES (1, 'foo'), (2, 'bar');
CREATE USER bob FOR LOGIN bob;
CREATE USER fred FOR LOGIN fred;
CREATE CLUSTERED INDEX thingsindex ON datadog_test_schemas_second.dbo.ϑings (name);
GO

-- Create an alternate collation database to test handling of case sensitivity
CREATE DATABASE datadog_test_collation
    COLLATE Latin1_General_100_BIN2;
GO
USE datadog_test_collation;
GO

CREATE SCHEMA test_schema;
GO

-- Create the partition function
CREATE PARTITION FUNCTION CityPartitionFunction (INT)
AS RANGE LEFT FOR VALUES (100, 200, 300); -- Define your partition boundaries here

-- Create the partition scheme
CREATE PARTITION SCHEME CityPartitionScheme
AS PARTITION CityPartitionFunction ALL TO ([PRIMARY]); -- Assign partitions to filegroups

-- Create the partitioned table
CREATE TABLE datadog_test_collation.test_schema.cities (
    id INT NOT NULL DEFAULT 0,
    name VARCHAR(255),
    population INT NOT NULL DEFAULT 0,
    CONSTRAINT PK_Cities PRIMARY KEY (id)
) ON CityPartitionScheme(id); -- Assign the partition scheme to the table

-- Create indexes
CREATE INDEX two_columns_index ON datadog_test_collation.test_schema.cities (id, name);
CREATE INDEX single_column_index ON datadog_test_collation.test_schema.cities (population);

INSERT INTO datadog_test_collation.test_schema.cities  VALUES (1, 'yey', 100), (2, 'bar', 200);
GO

-- Create table with a foreign key
CREATE TABLE datadog_test_collation.test_schema.landmarks (name varchar(255), city_id int DEFAULT 0);
GO
ALTER TABLE datadog_test_collation.test_schema.landmarks ADD CONSTRAINT FK_CityId FOREIGN KEY (city_id)
REFERENCES datadog_test_collation.test_schema.cities(id)
ON DELETE SET NULL;
GO

-- Create table with unique constraint
CREATE TABLE datadog_test_collation.test_schema.Restaurants (
    RestaurantName VARCHAR(255),
    District VARCHAR(100),
    Cuisine VARCHAR(100),
    CONSTRAINT UC_RestaurantNameDistrict UNIQUE (RestaurantName, District)
);
GO

-- Create table with a foreign key on two columns
CREATE TABLE datadog_test_collation.test_schema.RestaurantReviews (
    RestaurantName VARCHAR(255),
    District VARCHAR(100),
    Review VARCHAR(MAX),
    CONSTRAINT FK_RestaurantNameDistrict FOREIGN KEY (RestaurantName, District)
        REFERENCES datadog_test_collation.test_schema.Restaurants(RestaurantName, District)
        ON DELETE CASCADE
        ON UPDATE SET NULL
);
GO

-- Both indexes contain a, c, and e. key_columns and included_columns keep the key and INCLUDE list apart.
CREATE TABLE datadog_test_collation.test_schema.index_coverage (
    a INT,
    c INT,
    e INT
);
CREATE INDEX ix_include ON datadog_test_collation.test_schema.index_coverage (c) INCLUDE (a, e);
CREATE INDEX ix_prefix ON datadog_test_collation.test_schema.index_coverage (c, a) INCLUDE (e);
GO

-- ix_filtered covers only rows where e is not null.
CREATE INDEX ix_filtered ON datadog_test_collation.test_schema.index_coverage (a) WHERE e IS NOT NULL;
GO

-- Clustered (b, a) is not table column order, and ix_desc keeps the DESC suffix.
CREATE TABLE datadog_test_collation.test_schema.key_order (
    a INT,
    b INT,
    c INT,
    CONSTRAINT pk_key_order PRIMARY KEY CLUSTERED (b, a)
);
CREATE INDEX ix_desc ON datadog_test_collation.test_schema.key_order (c DESC, a);
GO

-- Create test database for integration tests
-- only bob and fred have read/write access to this database
-- the datadog user has only connect access but can't read any objects
CREATE DATABASE [datadog_test-1];
GO
USE [datadog_test-1];
GO

-- This table is pronounced "things" except we've replaced "th" with the greek lower case "theta" to ensure we
-- correctly support unicode throughout the integration.
CREATE TABLE [datadog_test-1].dbo.ϑings (id int, name varchar(255));
INSERT INTO [datadog_test-1].dbo.ϑings VALUES (1, 'foo'), (2, 'bar');
CREATE CLUSTERED INDEX thingsindex ON [datadog_test-1].dbo.ϑings (name);
CREATE USER bob FOR LOGIN bob;
CREATE USER fred FOR LOGIN fred;
-- we don't need to recreate the datadog user in this new DB because it already exists in the model
-- database so it's copied by default to new databases
GO

-- Create a simple table for deadlocks
CREATE TABLE [datadog_test-1].dbo.deadlocks (a int PRIMARY KEY not null ,b int null); 

INSERT INTO [datadog_test-1].dbo.deadlocks VALUES (1,10),(2,20),(3,30) 

-- Grant permissions to bob and fred to update the deadlocks table
GRANT INSERT ON [datadog_test-1].dbo.deadlocks TO bob;
GRANT UPDATE ON [datadog_test-1].dbo.deadlocks TO bob;
GRANT DELETE ON [datadog_test-1].dbo.deadlocks TO bob;

GRANT INSERT ON [datadog_test-1].dbo.deadlocks TO fred;
GRANT UPDATE ON [datadog_test-1].dbo.deadlocks TO fred;
GRANT DELETE ON [datadog_test-1].dbo.deadlocks TO fred;
GO

EXEC sp_addrolemember 'db_datareader', 'bob'
EXEC sp_addrolemember 'db_datareader', 'fred'
EXEC sp_addrolemember 'db_datawriter', 'bob'
GO

CREATE PROCEDURE bobProc AS
BEGIN
    SELECT * FROM ϑings;
END;
GO

CREATE PROCEDURE bobProcParams @P1 INT = NULL, @P2 nvarchar(8) = NULL AS
BEGIN
    SELECT * FROM ϑings WHERE id = @P1;
    SELECT id FROM ϑings WHERE name = @P2;
END;
GO

CREATE PROCEDURE fredProcParams @Name nvarchar(8) = NULL AS
BEGIN
    SELECT * FROM ϑings WHERE name like @Name;
END;
GO

GRANT EXECUTE on bobProcParams to bob;
GRANT EXECUTE on bobProc to bob;
GRANT EXECUTE on fredProcParams to fred;
GRANT EXECUTE on bobProc to fred;
GO


CREATE PROCEDURE procedureWithLargeCommment AS
/* 
author: Datadog 
usage: some random comments
test: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
description: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
this comment has no actual meanings, just to test large sp with truncation
the quick brown fox jumps over the lazy dog, the quick brown fox jumps over the lazy dog, the quick brown fox jumps over the lazy dog
*/
BEGIN
    SELECT * FROM ϑings;
END;
GO
GRANT EXECUTE on procedureWithLargeCommment to bob;
GRANT EXECUTE on procedureWithLargeCommment to fred;
GO

-- test procedure with embedded null characters
CREATE PROCEDURE nullCharTest
AS
BEGIN
 SELECT * FROM ϑings WHERE name = 'foo\x00';
END;
GO
GRANT EXECUTE on nullCharTest to bob;
GRANT EXECUTE on nullCharTest to fred;
GO

-- Column statistics: a database where the datadog user can run the column statistics procedure but can't read
-- the table. Data is deterministic so tests can assert exact statistics.
CREATE DATABASE datadog_test_column_stats;
GO
USE datadog_test_column_stats;
GO
CREATE TABLE dbo.orders (
    id INT NOT NULL PRIMARY KEY,
    customer_id INT NOT NULL,
    status VARCHAR(20) NULL,
    note NVARCHAR(100) NULL
);
CREATE INDEX ix_customer ON dbo.orders (customer_id);
CREATE INDEX ix_status ON dbo.orders (status);
INSERT INTO dbo.orders (id, customer_id, status, note)
SELECT n,
    CASE WHEN n % 10 < 3 THEN 7 ELSE n % 500 END,
    CASE WHEN n % 10 = 0 THEN NULL WHEN n % 10 IN (1, 2) THEN 'pending' ELSE 'shipped' END,
    REPLICATE(N'x', 20 + n % 21)
FROM (SELECT TOP 10000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n FROM sys.all_objects a CROSS JOIN sys.all_objects b) numbers;
CREATE STATISTICS st_note ON dbo.orders (note);
UPDATE STATISTICS dbo.orders WITH FULLSCAN;
GO
CREATE USER datadog FOR LOGIN datadog;
GO
CREATE SCHEMA datadog AUTHORIZATION dbo;
GO
CREATE OR ALTER PROCEDURE datadog.column_statistics @max_tables INT = 500
WITH EXECUTE AS OWNER
AS
BEGIN
    SET NOCOUNT ON;
    -- One statistics object per column: unfiltered, on the column as its leading key, the most fully sampled. Every
    -- value of a fixed-width type takes its storage size, so only variable-width columns need DBCC below.
    SELECT object_id, stats_id, stats_name, column_name, [rows], last_updated, fixed_width,
        CAST(NULL AS FLOAT) AS avg_width
    INTO #stats
    FROM (
        SELECT st.object_id, st.stats_id, st.name AS stats_name, c.name AS column_name, sp.[rows], sp.last_updated,
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

    -- Each histogram is read once; only whether a step is the NULL step is kept, never its value.
    SELECT s.object_id, s.stats_id, CASE WHEN hh.range_high_key IS NULL THEN 1 ELSE 0 END AS is_null,
        CAST(hh.equal_rows AS FLOAT) AS equal_rows, hh.distinct_range_rows
    INTO #hist
    FROM #stats s
    CROSS APPLY sys.dm_db_stats_histogram(s.object_id, s.stats_id) hh;

    -- Only counts and frequencies are returned, never the histogram's values. A common value is one with more rows
    -- than the column's average per value, as Postgres keeps in most_common_freqs. The width is averaged over non-NULL
    -- values, as in pg_stats; DBCC's average counts NULLs as zero bytes.
    SELECT OBJECT_SCHEMA_NAME(s.object_id) AS schema_name, OBJECT_NAME(s.object_id) AS table_name, s.column_name,
        DATEDIFF(SECOND, s.last_updated, SYSDATETIME()) AS stats_age,
        h.n_distinct, h.null_rows / s.[rows] AS null_frac,
        CASE WHEN s.fixed_width IS NOT NULL THEN s.fixed_width
            WHEN h.null_rows < s.[rows] THEN s.avg_width * s.[rows] / (s.[rows] - h.null_rows) END AS avg_width,
        m.most_common_freqs
    FROM #stats s
    CROSS APPLY (
        SELECT SUM(CASE WHEN hh.is_null = 1 THEN 0 ELSE 1 + hh.distinct_range_rows END) AS n_distinct,
            SUM(CASE WHEN hh.is_null = 1 THEN hh.equal_rows ELSE 0 END) AS null_rows
        FROM #hist hh
        WHERE hh.object_id = s.object_id AND hh.stats_id = s.stats_id
    ) h
    OUTER APPLY (
        SELECT STRING_AGG(f.freq, ',') WITHIN GROUP (ORDER BY f.equal_rows DESC) AS most_common_freqs
        FROM (
            SELECT hh.equal_rows, CONVERT(VARCHAR(32), hh.equal_rows / s.[rows], 3) AS freq
            FROM #hist hh
            WHERE hh.object_id = s.object_id AND hh.stats_id = s.stats_id AND hh.is_null = 0 AND h.n_distinct > 0
                AND hh.equal_rows > (s.[rows] - h.null_rows) / h.n_distinct
        ) f
    ) m
    ORDER BY schema_name, table_name, column_name;
END;
GO
GRANT EXECUTE ON datadog.column_statistics TO datadog;
GO
USE master;
GO

-- create an offline database to have an unavailable database to test with
CREATE DATABASE unavailable_db;
GO
ALTER DATABASE unavailable_db SET OFFLINE;
GO

-- create a a restricted database to ensure the agent gracefully handles not being able to connect
-- to it
CREATE DATABASE restricted_db;
GO
ALTER DATABASE restricted_db SET RESTRICTED_USER
GO

-- create test procedure for metrics loading feature
USE master;
GO
CREATE PROCEDURE pyStoredProc AS
BEGIN
    CREATE TABLE #Datadog
    (
        [metric] varchar(255) not null,
        [type] varchar(50) not null,
        [value] float not null,
        [tags] varchar(255)
    )
    SET NOCOUNT ON;
    INSERT INTO #Datadog (metric, type, value, tags) VALUES
                                                         ('sql.sp.testa', 'gauge', 100, 'foo:bar,baz:qux'),
                                                         ('sql.sp.testb', 'gauge', 1, 'foo:bar,baz:qux'),
                                                         ('sql.sp.testb', 'gauge', 2, 'foo:bar,baz:qux');
    SELECT * FROM #Datadog;
END;
GO
GRANT EXECUTE on pyStoredProc to datadog;
GO

CREATE PROCEDURE exampleProcWithoutNocount AS
BEGIN
    CREATE TABLE #Hello
    (
        [value] int not null,
    )
    INSERT INTO #Hello VALUES (1)
    select * from #Hello;
END;
GO
GRANT EXECUTE on exampleProcWithoutNocount to datadog;
GO

CREATE PROCEDURE encryptedProc WITH ENCRYPTION AS
BEGIN
    select count(*) from sys.databases;
END;
GO
GRANT EXECUTE on encryptedProc to bob;
GO

-- create test procedure with multiple queries
CREATE PROCEDURE multiQueryProc AS
BEGIN
    declare @total int = 0;
    select @total = @total + count(*) from sys.databases where name like '%_';
    select @total = @total + count(*) from sys.sysobjects where type = 'U';
    select @total;
END;
GO
GRANT EXECUTE on multiQueryProc to bob;
GO

-- test procedure with IF ELSE branches and temp tables
CREATE PROCEDURE conditionalPlanTest
 @Switch INTEGER
AS
BEGIN
 SET NOCOUNT ON
 CREATE TABLE #Ids (Id INTEGER PRIMARY KEY)

 IF (@Switch > 0)
  BEGIN
   INSERT INTO #Ids (Id) VALUES (1)
  END 

 IF (@Switch > 1)
  BEGIN
   INSERT #Ids (Id) VALUES (2)
  END

 SELECT * FROM #Ids
END
GO
GRANT EXECUTE on conditionalPlanTest to bob;
GO

CREATE EVENT SESSION datadog
ON SERVER
ADD EVENT sqlserver.xml_deadlock_report 
ADD TARGET package0.ring_buffer 
WITH (
    MAX_MEMORY = 1024 KB, 
    EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS, 
    MAX_DISPATCH_LATENCY = 120 SECONDS, 
    STARTUP_STATE = ON 
);
GO

ALTER EVENT SESSION datadog ON SERVER STATE = START;
GO

-- 1. Query completions (grouped)
-- Includes RPC completions, batch completions, and stored procedure completions
IF EXISTS (
    SELECT * FROM sys.server_event_sessions WHERE name = 'datadog_query_completions'
)
    DROP EVENT SESSION datadog_query_completions ON SERVER;
GO

CREATE EVENT SESSION datadog_query_completions ON SERVER
ADD EVENT sqlserver.rpc_completed (
    ACTION (
        sqlserver.sql_text,
        sqlserver.database_name,
        sqlserver.username,
        sqlserver.client_app_name,
        sqlserver.client_hostname,
        sqlserver.session_id,
        sqlserver.request_id
    )
    WHERE (
        sql_text <> '' AND
        duration > 1000000 -- in microseconds, 1 second
    )
),
ADD EVENT sqlserver.sql_batch_completed(
    ACTION (
        sqlserver.sql_text,
        sqlserver.database_name,
        sqlserver.username,
        sqlserver.client_app_name,
        sqlserver.client_hostname,
        sqlserver.session_id,
        sqlserver.request_id
    )
    WHERE (
        sql_text <> '' AND
        duration > 1000000
    )
),
ADD EVENT sqlserver.module_end(
    SET collect_statement = (1)
    ACTION (
        sqlserver.sql_text,
        sqlserver.database_name,
        sqlserver.username,
        sqlserver.client_app_name,
        sqlserver.client_hostname,
        sqlserver.session_id,
        sqlserver.request_id
    )
    WHERE (
        sql_text <> '' AND
        duration > 1000000
    )
)
ADD TARGET package0.ring_buffer
WITH (
    MAX_MEMORY = 2048 KB,
    TRACK_CAUSALITY = ON,
    EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS,
    MAX_DISPATCH_LATENCY = 3 SECONDS,
    STARTUP_STATE = ON
);
GO

-- 2. Errors and Attentions (grouped)
IF EXISTS (
    SELECT * FROM sys.server_event_sessions WHERE name = 'datadog_query_errors'
)
    DROP EVENT SESSION datadog_query_errors ON SERVER;
GO
CREATE EVENT SESSION datadog_query_errors ON SERVER
-- Low-frequency events: send to ring_buffer
ADD EVENT sqlserver.error_reported(
    ACTION(
        sqlserver.sql_text,
        sqlserver.database_name,
        sqlserver.username,
        sqlserver.client_app_name,
        sqlserver.client_hostname,
        sqlserver.session_id,
        sqlserver.request_id
    )
    WHERE severity >= 11
),
ADD EVENT sqlserver.attention(
    ACTION(
        sqlserver.sql_text,
        sqlserver.database_name,
        sqlserver.username,
        sqlserver.client_app_name,
        sqlserver.client_hostname,
        sqlserver.session_id,
        sqlserver.request_id
    )
)
ADD TARGET package0.ring_buffer
WITH (
    MAX_MEMORY = 2048 KB,
    EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS,
    MAX_DISPATCH_LATENCY = 30 SECONDS,
    STARTUP_STATE = ON
);

ALTER EVENT SESSION datadog_query_completions ON SERVER STATE = START;
ALTER EVENT SESSION datadog_query_errors ON SERVER STATE = START;