#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" datadog_test <<-EOSQL
    CREATE TABLE persons (personid SERIAL, lastname VARCHAR(255), firstname VARCHAR(255), address VARCHAR(255), city VARCHAR(255));
    INSERT INTO persons (lastname, firstname, address, city) VALUES ('Cavaille', 'Leo', 'Midtown', 'New York'), ('Someveryveryveryveryveryveryveryveryveryverylongname', 'something', 'Avenue des Champs Elysees', 'Beautiful city of lights');
    CREATE TABLE personsdup1 (personid SERIAL, lastname VARCHAR(255), firstname VARCHAR(255), address VARCHAR(255), city VARCHAR(255));
    INSERT INTO personsdup1 (lastname, firstname, address, city) VALUES ('Cavaille', 'Leo', 'Midtown', 'New York'), ('Someveryveryveryveryveryveryveryveryveryverylongname', 'something', 'Avenue des Champs Elysees', 'Beautiful city of lights');
    CREATE TABLE Personsdup2 (personid SERIAL, lastname VARCHAR(255), firstname VARCHAR(255), address VARCHAR(255), city VARCHAR(255));
    INSERT INTO Personsdup2 (lastname, firstname, address, city) VALUES ('Cavaille', 'Leo', 'Midtown', 'New York'), ('Someveryveryveryveryveryveryveryveryveryverylongname', 'something', 'Avenue des Champs Elysees', 'Beautiful city of lights');
    SELECT * FROM persons;
    SELECT * FROM persons;
    SELECT * FROM persons;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bob;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" dogs <<-EOSQL
    CREATE TABLE breed (id SERIAL, name VARCHAR(255));
    CREATE TABLE kennel (id SERIAL, address VARCHAR(255));
    INSERT INTO kennel (address) VALUES ('Midtown, New York'), ('Boston');
    SELECT * FROM kennel;
    CREATE INDEX breed_names ON breed(name);
    INSERT INTO breed (name) VALUES ('Labrador Retriver'), ('German Shepherd'), ('Yorkshire Terrier'), ('Golden Retriever'), ('Bulldog');
    SELECT * FROM breed WHERE name = 'Labrador';
EOSQL
