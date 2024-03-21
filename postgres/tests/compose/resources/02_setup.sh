#!/bin/bash
set -e

# pg_monitor is only available on 10+
# prior to version 10 there was no `pg_read_all_stats` role so by adding a database to which the agent can't connect
# it causes many of the tests to fail since some stats queries fail (like reading the size of the database to which you can't connect)
# therefore we will only add this database to which you can't connect in 10+ for testing purposes.
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

    CREATE OR REPLACE FUNCTION datadog.explain_statement(
      l_query TEXT,
      OUT explain JSON
    )
    RETURNS SETOF JSON AS
    $$
    DECLARE
    curs REFCURSOR;
    plan JSON;

    BEGIN
      OPEN curs FOR EXECUTE pg_catalog.concat('EXPLAIN (FORMAT JSON) ', l_query);
      FETCH curs INTO plan;
      CLOSE curs;
      RETURN QUERY SELECT plan;
    END;
    $$
    LANGUAGE 'plpgsql'
    RETURNS NULL ON NULL INPUT
    SECURITY DEFINER;

    CREATE OR REPLACE FUNCTION datadog.pg_stat_activity() RETURNS SETOF pg_stat_activity AS
    $$ SELECT * FROM pg_catalog.pg_stat_activity; $$
    LANGUAGE sql
    SECURITY DEFINER;

    ALTER FUNCTION datadog.explain_statement(l_query text, out explain json) OWNER TO postgres;
    ALTER FUNCTION datadog.pg_stat_activity() owner to postgres;

    -- datadog.explain_statement_noaccess is not part of the standard setup
    -- it's added only for the purpose of testing an explain function owned by a user with inadequate permissions
    CREATE OR REPLACE FUNCTION datadog.explain_statement_noaccess(
      l_query TEXT,
      OUT explain JSON
    )
    RETURNS SETOF JSON AS
    $$
    DECLARE
    curs REFCURSOR;
    plan JSON;

    BEGIN
      OPEN curs FOR EXECUTE pg_catalog.concat('EXPLAIN (FORMAT JSON) ', l_query);
      FETCH curs INTO plan;
      CLOSE curs;
      RETURN QUERY SELECT plan;
    END;
    $$
    LANGUAGE 'plpgsql'
    RETURNS NULL ON NULL INPUT
    SECURITY DEFINER;
    ALTER FUNCTION datadog.explain_statement_noaccess(l_query TEXT, OUT explain JSON) OWNER TO datadog;

    -- create dummy function to be executed to populate function metrics
    CREATE OR REPLACE FUNCTION dummy_function()
    RETURNS text AS
    $$
    BEGIN
        RETURN 'Hello, world!';
    END;
    $$
    LANGUAGE 'plpgsql'
    SECURITY DEFINER;
    ALTER FUNCTION dummy_function() OWNER TO datadog;
EOSQL
done

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" dogs_nofunc <<-'EOSQL'
    DROP FUNCTION datadog.explain_statement(l_query text, out explain JSON)
EOSQL

# Somehow, on old postgres version (11 and 12), wal_level is incorrectly set despite
# being present in postgresql.conf. Alter and restart to make sure we have the correct wal_level.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" datadog_test <<-'EOSQL'
    ALTER SYSTEM SET wal_level = logical;
EOSQL
pg_ctl -D /var/lib/postgresql/data -w restart

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" datadog_test <<-'EOSQL'
    SELECT * FROM pg_create_physical_replication_slot('replication_slot');
    SELECT * FROM pg_create_logical_replication_slot('logical_slot', 'test_decoding');
EOSQL
