#!/bin/bash

mongoimport --db dummy --collection restaurants --file /docker-entrypoint-initdb.d/restaurants.json
mongoimport --db dummy --collection employees --file /docker-entrypoint-initdb.d/employees.json
