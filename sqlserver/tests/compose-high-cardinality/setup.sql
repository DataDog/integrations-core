-- Datadog user
CREATE LOGIN datadog WITH PASSWORD = 'Password12!';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
GRANT CONNECT ANY DATABASE to datadog;
GRANT VIEW ANY DEFINITION to datadog;

-- Test users
CREATE LOGIN bob WITH PASSWORD = 'Password12!';
CREATE USER bob FOR LOGIN bob;
GRANT CONNECT ANY DATABASE to bob;
CREATE LOGIN fred WITH PASSWORD = 'Password12!';
CREATE USER fred FOR LOGIN fred;
GRANT CONNECT ANY DATABASE to fred;
GO

-- Create test database for integration tests
-- Only bob and fred have read/write access to this database
CREATE DATABASE datadog_test;
GO
USE datadog_test;
GO

-- Create a large table for testing. Complex data will be inserted from `dummy_data.sql`
-- The amount of rows to insert can be controlled in `setup.sh`
CREATE TABLE datadog_test.dbo.high_cardinality (
	id INT NOT NULL IDENTITY,
    guid TEXT,
    app_name TEXT,
    app_version TEXT,
    app_image TEXT,
    app_image_base64 TEXT,
    app_ip_v6 TEXT,
    app_btc_addr TEXT,
    app_slogan TEXT,
    app_priority INT,
    app_permissions INT,
    subscription_renewal TEXT,
    primary_contact TEXT,
    user_firstname TEXT,
    user_lastname TEXT,
    user_city TEXT,
    user_state TEXT,
    user_country TEXT,
    loc_lat DECIMAL,
    loc_long DECIMAL,
    user_ssn TEXT,
    user_card TEXT,
    user_card_type TEXT,
    created_at DATE,
    updated_at DATE,
	PRIMARY KEY (id)
);
CREATE USER bob FOR LOGIN bob;
CREATE USER fred FOR LOGIN fred;
GO

EXEC sp_addrolemember 'db_datareader', 'bob'
EXEC sp_addrolemember 'db_datawriter', 'bob'
EXEC sp_addrolemember 'db_datareader', 'fred'
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
