-----------------------------------
-- test db setup

-- datadog user
CREATE LOGIN datadog WITH PASSWORD = 'Password12!';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
GRANT CONNECT ANY DATABASE to datadog;
GRANT VIEW ANY DEFINITION to datadog;

USE msdb;
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT to datadog;

USE master;

-- test users
CREATE LOGIN bob WITH PASSWORD = 'Password12!';
CREATE USER bob FOR LOGIN bob;
GRANT CONNECT ANY DATABASE to bob;
GO

CREATE LOGIN fred WITH PASSWORD = 'Password12!';
CREATE USER fred FOR LOGIN fred;
GRANT CONNECT ANY DATABASE to fred;
GO

CREATE DATABASE [datadog_test-1];
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
ALTER TABLE datadog_test_schemas.test_schema.landmarks ADD CONSTRAINT FK_CityId FOREIGN KEY (city_id) REFERENCES datadog_test_schemas.test_schema.cities(id);
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
    CONSTRAINT FK_RestaurantNameDistrict FOREIGN KEY (RestaurantName, District) REFERENCES datadog_test_schemas.test_schema.Restaurants(RestaurantName, District)
);
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

-- Create test database for integration tests
-- only bob and fred have read/write access to this database
USE [datadog_test-1];
CREATE TABLE [datadog_test-1].dbo.ϑings (id int, name varchar(255));
INSERT INTO [datadog_test-1].dbo.ϑings VALUES (1, 'foo'), (2, 'bar');
CREATE CLUSTERED INDEX thingsindex ON [datadog_test-1].dbo.ϑings (name);
CREATE USER bob FOR LOGIN bob;
CREATE USER fred FOR LOGIN fred;
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

-----------------------------------
-- AGOG setup

USE [master]
GO

--change recovery model and take full backup for db to meet requirements of AOAG
ALTER DATABASE [datadog_test-1] SET RECOVERY FULL ;
GO

BACKUP DATABASE [datadog_test-1] TO  DISK = N'/var/opt/mssql/backup/[datadog_test-1].bak' WITH NOFORMAT, NOINIT,  NAME = N'[datadog_test-1]-Full Database Backup', SKIP, NOREWIND, NOUNLOAD,  STATS = 10
GO


--create logins for aoag
-- this password could also be originate from an environemnt variable passed in to this script through SQLCMD
CREATE LOGIN aoag_login WITH PASSWORD = 'Pa$$w0rd';
CREATE USER aoag_user FOR LOGIN aoag_login;

-- create certificate for AOAG
-- this password could also be originate from an environemnt variable passed in to this script through SQLCMD
CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'Pa$$w0rd';
GO

CREATE CERTIFICATE aoag_certificate WITH SUBJECT = 'aoag_certificate';
BACKUP CERTIFICATE aoag_certificate
TO FILE = '/var/opt/mssql/shared/aoag_certificate.cert'
WITH PRIVATE KEY (
        FILE = '/var/opt/mssql/shared/aoag_certificate.key',
        ENCRYPTION BY PASSWORD = 'Pa$$w0rd'
    );
GO

-- create HADR endpoint on port 5022
CREATE ENDPOINT [Hadr_endpoint]
STATE=STARTED
AS TCP (
    LISTENER_PORT = 5022,
    LISTENER_IP = ALL
)
FOR DATA_MIRRORING (
    ROLE = ALL,
    AUTHENTICATION = CERTIFICATE aoag_certificate,
    ENCRYPTION = REQUIRED ALGORITHM AES
)

GRANT CONNECT ON ENDPOINT::Hadr_endpoint TO [aoag_login];
GO



---------------------------------------------------------------------------------------------
--CREATE PRIMARY AG GROUP ON PRIMARY CLUSTER PRIMARY REPLICA
---------------------------------------------------------------------------------------------
--for clusterless AOAG the failover mode always needs to be manual

DECLARE @cmd AS NVARCHAR(MAX)

SET @cmd ='
CREATE AVAILABILITY GROUP [AG1]
WITH (
    CLUSTER_TYPE = NONE
)
FOR REPLICA ON
N''<SQLInstanceName>'' WITH
(
    ENDPOINT_URL = N''tcp://<SQLInstanceName>:5022'',
    AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
    SEEDING_MODE = AUTOMATIC,
    FAILOVER_MODE = MANUAL,
    SECONDARY_ROLE (ALLOW_CONNECTIONS = ALL)
),
N''aoag_secondary'' WITH
(
    ENDPOINT_URL = N''tcp://aoag_secondary:5022'',
    AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
    SEEDING_MODE = AUTOMATIC,
    FAILOVER_MODE = MANUAL,
    SECONDARY_ROLE (ALLOW_CONNECTIONS = ALL)
);
';

--replace local server name into the script above
DECLARE @create_ag AS nvarchar(max)
SELECT @create_ag = REPLACE(@cmd,'<SQLInstanceName>',@@SERVERNAME)

--execute creation of AOAG
exec sp_executesql @create_ag

--wait a bit and add database to AG
USE [master]
GO

WAITFOR DELAY '00:00:10'
ALTER AVAILABILITY GROUP [AG1] ADD DATABASE [datadog_test-1]
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
