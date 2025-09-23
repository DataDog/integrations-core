#!/bin/bash
# SQL script that performs SELECT, INSERT, CREATE, DELETE commands on a loop in cockroachdb.
# See /tests/README.md.

echo Wait for servers to be up
sleep 10

HOSTPARAMS="--host cockroachdb --insecure"
SQL="/cockroach/cockroach.sh sql $HOSTPARAMS"

while :
  do
    $SQL --watch 1m -e """
    CREATE DATABASE IF NOT EXISTS places;
    CREATE TABLE IF NOT EXISTS cities (
      id UUID NOT NULL DEFAULT gen_random_uuid(),
      city STRING NOT NULL,
      country STRING NOT NULL,
      population INT8 NOT NULL,
      CONSTRAINT \"primary\" PRIMARY KEY (city ASC, ID ASC)
    );
    INSERT INTO cities (city, country, population) VALUES ('New York City', 'USA', 8804190), ('Boston', 'USA', 654776), ('Madrid', 'Spain', 6975017), ('Paris', 'France', 2206488);
    SELECT * FROM cities;
    CREATE INDEX IF NOT EXISTS city_idx ON cities (city DESC);
    UPDATE cities SET population=10000000 WHERE city = 'New York City';
    INSERT INTO cities (city, country, population) VALUES ('Nowhere', 'USA', 0);
    SELECT city FROM cities WHERE population > 0;
    DELETE FROM cities WHERE city = 'Nowhere';
    DROP TABLE cities;
    SELECT * from fake_table;
    """

    random_num=$(( $RANDOM % 300 + 60 ))

    if [ $(random_num % 2) -gt 275 ]; then
      $SQL -e "SELECT * from fake_table;"
    fi

    echo Sleeping...
    sleep random_num
  done
