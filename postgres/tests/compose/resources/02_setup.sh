#!/bin/bash
set -e

# pg_monitor is only available on 10+
# prior to version 10 there was no `pg_read_all_stats` role so by adding a database to which the agent can't connect
# it causes many of the tests to fail since some stats queries fail (like reading the size of the database to which you can't connect)
# therefore we will only add this database to which you can't connect in 10+ for testing purposes
if [[ !("$PG_MAJOR" == 9.* ) ]]; then
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" datadog_test <<-'EOSQL'
    GRANT pg_monitor TO datadog;
EOSQL
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" "datadog_test" <<-'EOSQL'
    CREATE EXTENSION pg_stat_statements SCHEMA public;
    GRANT SELECT ON pg_stat_statements TO datadog;

    CREATE SCHEMA IF NOT EXISTS datadog;
    GRANT USAGE ON SCHEMA datadog TO datadog;

    CREATE OR REPLACE FUNCTION datadog.pg_stat_statements() RETURNS SETOF pg_stat_statements AS
      $$ SELECT * FROM pg_stat_statements; $$
    LANGUAGE sql
    SECURITY DEFINER;

    ALTER FUNCTION datadog.pg_stat_statements() owner to postgres;
EOSQL

# dogs_noschema deliberately excluded
for DBNAME in datadog_test dogs dogs_nofunc; do

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" "$DBNAME" <<-'EOSQL'
    CREATE SCHEMA IF NOT EXISTS datadog;
    GRANT USAGE ON SCHEMA datadog TO datadog;

    CREATE OR REPLACE FUNCTION datadog.explain_statement(l_query text, out explain JSON) RETURNS SETOF JSON AS
    $$
      BEGIN
          RETURN QUERY EXECUTE 'EXPLAIN (FORMAT JSON) ' || l_query;
      END;
    $$
    LANGUAGE plpgsql
    RETURNS NULL ON NULL INPUT
    SECURITY DEFINER;

    CREATE OR REPLACE FUNCTION datadog.pg_stat_activity() RETURNS SETOF pg_stat_activity AS
    $$ SELECT * FROM pg_catalog.pg_stat_activity; $$
    LANGUAGE sql
    SECURITY DEFINER;

    ALTER FUNCTION datadog.explain_statement(l_query text, out explain json) OWNER TO postgres;
    ALTER FUNCTION datadog.pg_stat_activity() owner to postgres;
EOSQL

done

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" dogs_nofunc <<-'EOSQL'
    DROP FUNCTION datadog.explain_statement(l_query text, out explain JSON)
EOSQL
