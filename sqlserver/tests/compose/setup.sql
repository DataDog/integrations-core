-- datadog user
CREATE LOGIN datadog WITH PASSWORD = 'Password12!';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
GRANT CONNECT ANY DATABASE to datadog;
GRANT VIEW ANY DEFINITION to datadog;
GRANT CREATE TYPE TO datadog;

-- test users
CREATE LOGIN bob WITH PASSWORD = 'Password12!';
CREATE USER bob FOR LOGIN bob;
GRANT CONNECT ANY DATABASE to bob;
CREATE LOGIN fred WITH PASSWORD = 'Password12!';
CREATE USER fred FOR LOGIN fred;
GRANT CONNECT ANY DATABASE to fred;
GO


CREATE DATABASE datadog_test_schemas;
GO
USE datadog_test_schemas;
GO

CREATE SCHEMA test_schema;
GO

--CREATE TABLE datadog_test_schemas.test_schema.cities (id int DEFAULT 0, name varchar(255));
--GO
--ALTER TABLE datadog_test_schemas.test_schema.cities
--ALTER COLUMN id INT NOT NULL;
--GO
--CREATE INDEX two_columns_index ON datadog_test_schemas.test_schema.cities (id, name);
--ALTER TABLE datadog_test_schemas.test_schema.cities
--ADD CONSTRAINT PK_Cities PRIMARY KEY (id);
--GO

--CREATE TABLE datadog_test_schemas.test_schema.cities (
--    id INT NOT NULL DEFAULT 0,
--    name VARCHAR(255),
--    CONSTRAINT PK_Cities PRIMARY KEY (id)
--);

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
    CONSTRAINT PK_Cities PRIMARY KEY (id)
) ON CityPartitionScheme(id); -- Assign the partition scheme to the table


CREATE INDEX two_columns_index ON datadog_test_schemas.test_schema.cities (id, name);

INSERT INTO datadog_test_schemas.test_schema.cities  VALUES (1, 'yey'), (2, 'bar');
GO
CREATE TABLE datadog_test_schemas.test_schema.landmarks (name varchar(255), city_id int DEFAULT 0);
GO
ALTER TABLE datadog_test_schemas.test_schema.landmarks ADD CONSTRAINT FK_CityId FOREIGN KEY (city_id) REFERENCES datadog_test_schemas.test_schema.cities(id);
GO

--------------------------------------------------
CREATE TABLE datadog_test_schemas.test_schema.Restaurants (
    RestaurantName VARCHAR(255),
    District VARCHAR(100),
    Cuisine VARCHAR(100),
    CONSTRAINT UC_RestaurantNameDistrict UNIQUE (RestaurantName, District)
);
GO

CREATE TABLE datadog_test_schemas.test_schema.RestaurantReviews (
    RestaurantName VARCHAR(255),
    District VARCHAR(100),
    Review VARCHAR(MAX),
    CONSTRAINT FK_RestaurantNameDistrict FOREIGN KEY (RestaurantName, District) REFERENCES datadog_test_schemas.test_schema.Restaurants(RestaurantName, District)
);
GO

-- Start of populate.sql
DECLARE @TableNamePrefix NVARCHAR(100) = 'dbm_employee_boris';
DECLARE @Index INT = 1;
DECLARE @MaxTables INT = 10000;

WHILE @Index <= @MaxTables
BEGIN
    DECLARE @TableName NVARCHAR(200) = @TableNamePrefix + '_' + CAST(@Index AS NVARCHAR(10));
    DECLARE @SQL NVARCHAR(MAX);

    SET @SQL = '
        CREATE TABLE ' + QUOTENAME(@TableName) + ' (
            id INT NOT NULL IDENTITY PRIMARY KEY,
            username VARCHAR(200),
            nickname VARCHAR(200),
            email VARCHAR(200),
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE(),
            username2 VARCHAR(200),
username3 VARCHAR(200),
username4 VARCHAR(200),
username5 VARCHAR(200),
username6 VARCHAR(200),
username7 VARCHAR(200),
username8 VARCHAR(200),
username9 VARCHAR(200),
username10 VARCHAR(200),
username11 VARCHAR(200),
username12 VARCHAR(200),
username13 VARCHAR(200),
username14 VARCHAR(200),
username15 VARCHAR(200),
username16 VARCHAR(200),
username17 VARCHAR(200),
username18 VARCHAR(200),
username19 VARCHAR(200),
username20 VARCHAR(200),
username21 VARCHAR(200),
username22 VARCHAR(200),
username23 VARCHAR(200),
username24 VARCHAR(200),
username25 VARCHAR(200),
username26 VARCHAR(200),
username27 VARCHAR(200),
username28 VARCHAR(200),
username29 VARCHAR(200),
username30 VARCHAR(200),
username31 VARCHAR(200),
username32 VARCHAR(200),
username33 VARCHAR(200),
username34 VARCHAR(200),
username35 VARCHAR(200),
username36 VARCHAR(200),
username37 VARCHAR(200),
username38 VARCHAR(200),
username39 VARCHAR(200),
username40 VARCHAR(200),
username41 VARCHAR(200),
username42 VARCHAR(200),
username43 VARCHAR(200),
username44 VARCHAR(200),
username45 VARCHAR(200),
username46 VARCHAR(200),
username47 VARCHAR(200),
username48 VARCHAR(200),
username49 VARCHAR(200),
username50 VARCHAR(200)
        );';

    EXEC sp_executesql @SQL, N'@TableNamePrefix NVARCHAR(100)', @TableNamePrefix;

    SET @Index = @Index + 1;
END;
-- End of populate.sql

-- Create test database for integration tests
-- only bob and fred have read/write access to this database
CREATE DATABASE datadog_test;
GO
USE datadog_test;
GO


-- This table is pronounced "things" except we've replaced "th" with the greek lower case "theta" to ensure we
-- correctly support unicode throughout the integration.

CREATE TABLE datadog_test.dbo.ϑings (id int DEFAULT 0, name varchar(255));
INSERT INTO datadog_test.dbo.ϑings VALUES (1, 'foo'), (2, 'bar');
CREATE USER bob FOR LOGIN bob;
CREATE USER fred FOR LOGIN fred;
CREATE CLUSTERED INDEX thingsindex ON datadog_test.dbo.ϑings (name);
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

GRANT EXECUTE on bobProcParams to bob;
GRANT EXECUTE on bobProc to bob;
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
