
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

USE msdb;
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT to datadog;

USE master;

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