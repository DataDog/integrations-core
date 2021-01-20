# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT1 = 27017
PORT2 = 27018
PORT_ARBITER = 27020
MAX_WAIT = 150

MONGODB_SERVER = "mongodb://%s:%s/test" % (HOST, PORT1)
SHARD_SERVER = "mongodb://%s:%s/test" % (HOST, PORT2)
MONGODB_VERSION = os.environ['MONGO_VERSION']

ROOT = os.path.dirname(os.path.dirname(HERE))

INSTANCE_BASIC = {'hosts': ['{}:{}'.format(HOST, PORT1)]}
INSTANCE_BASIC_SHARD = {'hosts': ['{}:{}'.format(HOST, PORT2)]}
INSTANCE_BASIC_LEGACY_CONFIG = {'server': MONGODB_SERVER}

INSTANCE_AUTHDB = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser',
    'password': 'testPass',
    'options': {'authSource': 'authDB'},
}
INSTANCE_AUTHDB_ALT = {
    # Include special cases, e.g. default port and special characters
    'hosts': [HOST],
    'database': 'test',
    'username': 'special test user',
    'password': 's3\\kr@t',
    'options': {'authSource': 'authDB'},
}
INSTANCE_AUTHDB_LEGACY_CONFIG = {
    'server': 'mongodb://testUser:testPass@{}:{}/test?authSource=authDB'.format(HOST, PORT1)
}

INSTANCE_USER = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser2',
    'password': 'testPass2',
}
INSTANCE_USER_LEGACY_CONFIG = {'server': 'mongodb://testUser2:testPass2@{}:{}/test'.format(HOST, PORT1)}

INSTANCE_ARBITER = {'hosts': ['{}:{}'.format(HOST, PORT_ARBITER)], 'username': 'testUser', 'password': 'testPass'}
