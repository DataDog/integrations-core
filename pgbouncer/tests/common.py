# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from packaging import version

from datadog_checks.base.utils.common import get_docker_hostname

HOST = get_docker_hostname()
PORT = '6432'
USER = 'postgres'
PASS = 'd@tadog'
DB = 'datadog_test'

DEFAULT_INSTANCE = {'host': HOST, 'port': PORT, 'username': USER, 'password': PASS, 'tags': ['optional:tag1']}
INSTANCE_NO_PASS = {'host': 'localhost', 'port': PORT, 'username': USER, 'tags': ['optional:tag1']}

INSTANCE_URL = {
    'database_url': 'postgresql://{}:d%40tadog@{}:{}/pgbouncer'.format(USER, HOST, PORT),
    'tags': ['optional:tag1'],
}


def get_version_from_env():
    return version.parse(os.environ.get('PGBOUNCER_VERSION'))
