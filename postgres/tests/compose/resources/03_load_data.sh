#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" datadog_test <<-EOSQL
    CREATE TABLE cities (city VARCHAR(255), country VARCHAR(255), PRIMARY KEY(city));
    INSERT INTO cities VALUES ('New York', 'USA'), ('Beautiful city of lights', 'France');
    CREATE TABLE persons (personid SERIAL, lastname VARCHAR(255), firstname VARCHAR(255), address VARCHAR(255), city VARCHAR(255) DEFAULT 'New York',  CONSTRAINT fk_city FOREIGN KEY (city) REFERENCES cities(city));
    INSERT INTO persons (lastname, firstname, address, city) VALUES ('Cavaille', 'Leo', 'Midtown', 'New York'), ('Someveryveryveryveryveryveryveryveryveryverylongname', 'something', 'Avenue des Champs Elysees', 'Beautiful city of lights');
    CREATE TABLE personsdup1 AS TABLE persons;
    CREATE TABLE personsdup2 AS TABLE persons;
    CREATE TABLE personsdup3 AS TABLE persons;
    CREATE TABLE personsdup4 AS TABLE persons;
    CREATE TABLE personsdup5 AS TABLE persons;
    CREATE TABLE personsdup6 AS TABLE persons;
    CREATE TABLE personsdup7 AS TABLE persons;
    CREATE TABLE personsdup8 AS TABLE persons;
    CREATE TABLE personsdup9 AS TABLE persons;
    CREATE TABLE personsdup10 AS TABLE persons;
    CREATE TABLE personsdup11 AS TABLE persons;
    CREATE TABLE personsdup12 AS TABLE persons;
    CREATE TABLE personsdup13 AS TABLE persons;
    CREATE TABLE persons_indexed AS TABLE persons;
    ALTER TABLE persons_indexed ADD PRIMARY KEY (personid);
    CREATE TABLE pgtable (personid SERIAL, lastname VARCHAR(255), firstname VARCHAR(255), address VARCHAR(255), city VARCHAR(255));
    INSERT INTO pgtable (lastname, firstname, address, city) VALUES ('Cavaille', 'Leo', 'Midtown', 'New York'), ('Someveryveryveryveryveryveryveryveryveryverylongname', 'something', 'Avenue des Champs Elysees', 'Beautiful city of lights');
    CREATE TABLE pg_newtable (personid SERIAL, lastname VARCHAR(255), firstname VARCHAR(255), address VARCHAR(255), city VARCHAR(255));
    INSERT INTO pg_newtable (lastname, firstname, address, city) VALUES ('Cavaille', 'Leo', 'Midtown', 'New York'), ('Someveryveryveryveryveryveryveryveryveryverylongname', 'something', 'Avenue des Champs Elysees', 'Beautiful city of lights');
    SELECT * FROM persons;
    SELECT * FROM persons;
    SELECT * FROM persons;
    CREATE SCHEMA public2;
    CREATE TABLE public2.cities (city VARCHAR(255), country VARCHAR(255), PRIMARY KEY(city));
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bob;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO blocking_bob;
EOSQL

# Create publication for logical replication tests
if [[ !("$PG_MAJOR" == 9.*) ]]; then
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -p5432 datadog_test <<-EOSQL
    CREATE PUBLICATION publication_persons for table persons_indexed;
    CREATE PUBLICATION publication_cities for table cities;
    CREATE PUBLICATION publication_persons_2 for table persons_indexed;
EOSQL
fi

if [[ !("$PG_MAJOR" == 9.*) && !("$PG_MAJOR" == 10) ]]; then
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" datadog_test <<-EOSQL
    CREATE TABLE test_part (id SERIAL PRIMARY KEY, filler text) PARTITION BY RANGE (id);
    CREATE TABLE test_part1 PARTITION OF test_part FOR VALUES FROM (MINVALUE) TO (500);
    CREATE TABLE test_part2 PARTITION OF test_part FOR VALUES FROM (500) TO (MAXVALUE);
    CREATE INDEX test_part_id ON test_part(id);
    INSERT INTO test_part (filler) SELECT * FROM generate_series(1, 2000);
    INSERT INTO test_part (filler) SELECT array_to_string(ARRAY(SELECT chr((65 + round(random() * 50)) :: integer) FROM generate_series(1,3000)), '');
    VACUUM ANALYZE test_part;
    CREATE TABLE test_part_no_children (id SERIAL PRIMARY KEY, filler text) PARTITION BY RANGE (id);
    CREATE TABLE test_part_no_activity (id SERIAL PRIMARY KEY, filler text) PARTITION BY RANGE (id);
    CREATE TABLE test_part_no_activity1 PARTITION OF test_part_no_activity FOR VALUES FROM (MINVALUE) TO (500);
    CREATE TABLE test_part_no_activity2 PARTITION OF test_part_no_activity FOR VALUES FROM (500) TO (MAXVALUE);
EOSQL
fi

for DBNAME in dogs dogs_noschema dogs_nofunc; do

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" "$DBNAME" <<-EOSQL
    CREATE TABLE breed (id SERIAL, name VARCHAR(255));
    CREATE TABLE kennel (id SERIAL, address VARCHAR(255));
    INSERT INTO kennel (address) VALUES ('Midtown, New York'), ('Boston');
    SELECT * FROM kennel;
    CREATE INDEX breed_names ON breed(name);
    INSERT INTO breed (name) VALUES ('Labrador Retriver'), ('German Shepherd'), ('Yorkshire Terrier'), ('Golden Retriever'), ('Bulldog');
    SELECT * FROM breed WHERE name = 'Labrador';
EOSQL

done
