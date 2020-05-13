# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.base.utils.common import get_docker_hostname

HOST = get_docker_hostname()
PORT = '6432'
USER = 'postgres'
PASS = 'datadog'
DB = 'datadog_test'

DEFAULT_INSTANCE = {'host': HOST, 'port': PORT, 'username': USER, 'password': PASS, 'tags': ['optional:tag1']}

INSTANCE_URL = {'database_url': 'postgresql://datadog:datadog@localhost:16432/datadog_test', 'tags': ['optional:tag1']}


def get_version_from_env():
    return os.environ.get('PGBOUNCER_VERSION').replace('_', '.').split('.')
