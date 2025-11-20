ALTER SYSTEM SET max_connections = '1000';
ALTER SYSTEM SET shared_buffers = '240MB';

CREATE USER datadog WITH PASSWORD 'datadog';
CREATE USER datadog_no_catalog WITH PASSWORD 'datadog';
CREATE USER bob WITH PASSWORD 'bob';
CREATE USER blocking_bob WITH PASSWORD 'bob';
CREATE USER dd_admin WITH PASSWORD 'dd_admin';
CREATE USER replicator WITH REPLICATION;
ALTER USER dd_admin WITH SUPERUSER;
REVOKE SELECT ON ALL tables IN SCHEMA pg_catalog from public;
GRANT SELECT ON pg_stat_database TO datadog;
GRANT SELECT ON pg_stat_database TO datadog_no_catalog;
GRANT SELECT ON ALL tables IN SCHEMA pg_catalog to datadog;
CREATE DATABASE datadog_test;
GRANT ALL PRIVILEGES ON DATABASE datadog_test TO datadog;
CREATE DATABASE dogs;
GRANT USAGE on SCHEMA public to bob;
GRANT USAGE on SCHEMA public to blocking_bob;
CREATE DATABASE dogs_nofunc;
CREATE DATABASE dogs_noschema;

-- These databases should get excluded from database autodiscovery by default
CREATE DATABASE rdsadmin;
CREATE DATABASE cloudsqladmin;
CREATE DATABASE alloydbadmin;
CREATE DATABASE alloydbmetadata;

-- These databases must be enumerated like so because postgres does
-- not support the creation of databases in a transaction so functions
-- cannot be used to accomplish this same task. Anyone aware of a better
-- implementation is welcome to change it.
CREATE DATABASE dogs_0;
CREATE DATABASE dogs_1;
CREATE DATABASE dogs_2;
CREATE DATABASE dogs_3;
CREATE DATABASE dogs_4;
CREATE DATABASE dogs_5;
CREATE DATABASE dogs_6;
CREATE DATABASE dogs_7;
CREATE DATABASE dogs_8;
CREATE DATABASE dogs_9;
