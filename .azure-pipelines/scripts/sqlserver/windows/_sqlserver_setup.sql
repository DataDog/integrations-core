-- this setup is the same as the setup done for the docker-based sql server tests in the sqlserver integration
ALTER LOGIN sa with PASSWORD = 'Password12!';
ALTER LOGIN sa ENABLE;

-- datadog user
CREATE LOGIN datadog WITH PASSWORD = 'Password12!';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
GRANT CONNECT ANY DATABASE to datadog;
GRANT VIEW ANY DEFINITION to datadog;

-- test users
CREATE LOGIN bob WITH PASSWORD = 'Password12!';
CREATE USER bob FOR LOGIN bob;
GRANT CONNECT ANY DATABASE to bob;

-- Create test database for integration tests
-- only bob has read/write access to this database
CREATE DATABASE datadog_test;
GO
USE datadog_test;
CREATE TABLE datadog_test.dbo.ϑings (id int, name varchar(255));
INSERT INTO datadog_test.dbo.ϑings VALUES (1, 'foo'), (2, 'bar');
CREATE USER bob FOR LOGIN bob;
GO

EXEC sp_addrolemember 'db_datareader', 'bob'
EXEC sp_addrolemember 'db_datawriter', 'bob'
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
