# E2E

## Populate `cockroachdb.sql.*` metrics

You may want to populate the `cockroachdb.sql` metrics for development purposes or for generating sample data such as for a dashboard. Included in the `/tests/docker/` directory is a SQL script, `sql.sh`, that runs various SQL commands on a loop. To run this script, enable the E2E cockroachdb container by doing the following: `POPULATE_METRICS="true" ddev env start cockroachdb py3.9-22.1`
