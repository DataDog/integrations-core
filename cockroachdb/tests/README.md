# E2E

## Populate `cockroachdb.sql.*` metrics

You may want to populate the `cockroachdb.sql` metrics for development purposes or for generating sample data such as for a dashboard. Included in the `/tests/docker/` directory is a SQL script, `sql.sh`, that runs various SQL commands on a loop. To enable the E2E cockroachdb container to run this script do the following:

1. `docker-compose.yaml`: Uncomment the `volumes` section to mount the `sql.sh` file to the cockroachdb container.
2. `conftest.py`: Uncomment the `run_sql` condition in the `dd_environment` function.
