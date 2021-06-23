
--create sample database
USE [master]
GO
CREATE DATABASE Sales
GO
USE [SALES]
GO
CREATE TABLE CUSTOMER([CustomerID] [int] NOT NULL, [SalesAmount] [decimal] NOT NULL)
GO
INSERT INTO CUSTOMER (CustomerID, SalesAmount) VALUES (1,100),(2,200),(3,300)

--change recovery model and take full backup for db to meet requirements of AOAG
ALTER DATABASE [SALES] SET RECOVERY FULL ;
GO

BACKUP DATABASE [Sales] TO  DISK = N'/var/opt/mssql/backup/Sales.bak' WITH NOFORMAT, NOINIT,  NAME = N'Sales-Full Database Backup', SKIP, NOREWIND, NOUNLOAD,  STATS = 10
GO

USE [master]
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
ALTER AVAILABILITY GROUP [AG1] ADD DATABASE [SALES]
GO
