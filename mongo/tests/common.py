# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT1 = 27017
PORT2 = 27018
MAX_WAIT = 150

MONGODB_SERVER = "mongodb://%s:%s/test" % (HOST, PORT1)
MONGODB_VERSION = os.environ['MONGO_VERSION']

ROOT = os.path.dirname(os.path.dirname(HERE))

INSTANCE_BASIC = {'hosts': ['{}:{}'.format(HOST, PORT1)]}
INSTANCE_BASIC_LEGACY_CONFIG = {'server': MONGODB_SERVER}

INSTANCE_AUTHDB = {
    'hosts': ['{}:{}'.format(HOST, PORT1)],
    'database': 'test',
    'username': 'testUser',
    'password': 'testPass',
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
