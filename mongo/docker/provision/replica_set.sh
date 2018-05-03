#!/bin/bash

sleep 2

mongo mongo-rep1:27017 --eval 'rs.initiate()'
mongo mongo-rep1:27017 --eval 'rs.add("mongo-rep2")'
mongo mongo-rep1:27017 --eval 'rs.add("mongo-rep3")'

mongoimport -h mongo-rep1 --db dummy --collection restaurants --file /_assets/json/restaurants.json
mongoimport -h mongo-rep1 --db dummy --collection employees --file /_assets/json/employees.json
