
USE [master]
GO

CREATE LOGIN bob WITH PASSWORD = 'Password12!';
CREATE USER bob FOR LOGIN bob;
GRANT CONNECT ANY DATABASE to bob;
CREATE LOGIN fred WITH PASSWORD = 'Password12!';
CREATE USER fred FOR LOGIN fred;
GRANT CONNECT ANY DATABASE to fred;
GO

CREATE LOGIN datadog WITH PASSWORD = 'Password12!';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
GRANT CONNECT ANY DATABASE to datadog;
GRANT VIEW ANY DEFINITION to datadog;

--create login for aoag
-- this password could also be originate from an environemnt variable passed in to this script through SQLCMD
-- it should however, match the password from the primary script
CREATE LOGIN aoag_login WITH PASSWORD = 'Pa$$w0rd';
CREATE USER aoag_user FOR LOGIN aoag_login;

-- create certificate
-- this time, create the certificate using the certificate file created in the primary node
CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'Pa$$w0rd';
GO

-- this password could also be originate from an environemnt variable passed in to this script through SQLCMD
-- it should however, match the password from the primary script
CREATE CERTIFICATE aoag_certificate
    AUTHORIZATION aoag_user
    FROM FILE = '/var/opt/mssql/shared/aoag_certificate.cert'
    WITH PRIVATE KEY (
    FILE = '/var/opt/mssql/shared/aoag_certificate.key',
    DECRYPTION BY PASSWORD = 'Pa$$w0rd'
)
GO

--create HADR endpoint

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

--add current node to the availability group

ALTER AVAILABILITY GROUP [AG1] JOIN WITH (CLUSTER_TYPE = NONE)
ALTER AVAILABILITY GROUP [AG1] GRANT CREATE ANY DATABASE
GO
