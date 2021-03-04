CREATE USER datadog WITH PASSWORD 'datadog';
CREATE USER bob WITH PASSWORD 'bob';
CREATE USER dd_admin WITH PASSWORD 'dd_admin';
ALTER USER dd_admin WITH SUPERUSER;
GRANT SELECT ON pg_stat_database TO datadog;
CREATE DATABASE datadog_test;
GRANT ALL PRIVILEGES ON DATABASE datadog_test TO datadog;
CREATE DATABASE dogs;
GRANT USAGE on SCHEMA public to bob;
