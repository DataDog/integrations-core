# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

HERE = os.path.dirname(os.path.abspath(__file__))

CHECK_NAME = 'mysql'

HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')
PORT = '13306'
SLAVE_PORT = '13307'

METRIC_TAGS = ['tag1', 'tag2']

MYSQL_MINIMAL_CONFIG = {
    'server': HOST,
    'user': 'dog',
    'pass': 'dog',
    'port': PORT
}

MYSQL_COMPLEX_CONFIG = {
    'server': HOST,
    'user': 'dog',
    'pass': 'dog',
    'port': PORT,
    'options': {
        'replication': True,
        'extra_status_metrics': True,
        'extra_innodb_metrics': True,
        'extra_performance_metrics': True,
        'schema_size_metrics': True,
    },
    'tags': METRIC_TAGS,
    'queries': [
        {
            'query': "SELECT * from testdb.users where name='Alice' limit 1;",
            'metric': 'alice.age',
            'type': 'gauge',
            'field': 'age'
        },
        {
            'query': "SELECT * from testdb.users where name='Bob' limit 1;",
            'metric': 'bob.age',
            'type': 'gauge',
            'field': 'age'
        }
    ]
}

CONNECTION_FAILURE = {
    'server': HOST,
    'user': 'unknown',
    'pass': 'dog',
}


"""
exec mysql -h"$MYSQL_PORT_3306_TCP_ADDR" -P"MYSQL_PORT_3306_TCP_PORT" -uroot \
     #{opts} -e "create user \"dog\"@\"%\" identified by \"dog\"; \
     GRANT PROCESS, REPLICATION CLIENT ON *.* TO \"dog\"@\"%\" WITH MAX_USER_CONNECTIONS 5; \
     CREATE DATABASE testdb; \
     CREATE TABLE testdb.users (name VARCHAR(20), age INT); \
     GRANT SELECT ON testdb.users TO \"dog\"@\"%\"; \
     INSERT INTO testdb.users (name,age) VALUES(\"Alice\",25); \
     INSERT INTO testdb.users (name,age) VALUES(\"Bob\",20); \
     GRANT SELECT ON performance_schema.* TO \"dog\"@\"%\"; \
     USE testdb; \
     SELECT * FROM users ORDER BY name; "
"""
