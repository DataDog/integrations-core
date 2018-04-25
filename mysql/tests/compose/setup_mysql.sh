#!/bin/bash

MYSQL_SCRIPT_OPTIONS=${MYSQL_SCRIPT_OPTIONS:-''}

mysql -h"mysql-master" -P"3306" -uroot \
     ${MYSQL_SCRIPT_OPTIONS} \
     -e "create user \"dog\"@\"%\" identified by \"dog\"; \
     GRANT PROCESS, REPLICATION CLIENT ON *.* TO \"dog\"@\"%\" WITH MAX_USER_CONNECTIONS 5; \
     CREATE DATABASE testdb; \
     CREATE TABLE testdb.users (name VARCHAR(20), age INT); \
     GRANT SELECT ON testdb.users TO \"dog\"@\"%\"; \
     INSERT INTO testdb.users (name,age) VALUES(\"Alice\",25); \
     INSERT INTO testdb.users (name,age) VALUES(\"Bob\",20); \
     GRANT SELECT ON performance_schema.* TO \"dog\"@\"%\"; \
     USE testdb; \
     SELECT * FROM users ORDER BY name;"
