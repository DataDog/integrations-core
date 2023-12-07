# Data was already transfered during pg_basebackup
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" datadog_test <<-EOSQL
CREATE SUBSCRIPTION subscription_persons CONNECTION 'port=5432 host=postgres user=dd_admin password=dd_admin dbname=datadog_test' PUBLICATION publication_persons WITH (copy_data=false);
CREATE SUBSCRIPTION subscription_cities CONNECTION 'port=5432 host=postgres user=dd_admin password=dd_admin dbname=datadog_test' PUBLICATION publication_cities;
CREATE SUBSCRIPTION subscription_persons2 CONNECTION 'port=5432 host=postgres user=dd_admin password=dd_admin dbname=datadog_test' PUBLICATION publication_persons_2 WITH (enabled=false);
INSERT INTO persons_indexed (personid, lastname, firstname, address, city) VALUES (3, 'Another', 'Person', 'will conflict', 'New York');
EOSQL

# Insert data on the primary that will conflict with the logical replication
PGPASSWORD=$POSTGRES_PASSWORD psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -h postgres -p5432 datadog_test <<-EOSQL
    INSERT INTO persons_indexed (personid, lastname, firstname, address, city) VALUES (3, 'Another', 'Person', 'will conflict', 'New York');
EOSQL
