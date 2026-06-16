# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

HOST = get_docker_hostname()
PORT = '50000'
DB = 'datadog'
USERNAME = 'db2inst1'
PASSWORD = 'db2inst1-pwd'
DBM_USERNAME = 'datadog'
DBM_PASSWORD = 'datadog-pwd'
DB2_IMAGE = os.getenv('DB2_IMAGE', 'taskana/db2')
DB2_VERSION = os.getenv('DB2_VERSION')


def is_db2_version_at_least(major: int, minor: int) -> bool:
    if not DB2_VERSION:
        return False

    try:
        version = tuple(int(part) for part in DB2_VERSION.split('.')[:2])
    except ValueError:
        return False

    return version >= (major, minor)


requires_db2_12_1 = pytest.mark.skipif(
    not is_db2_version_at_least(12, 1), reason='DBM integration tests require Db2 12.1+'
)

CONFIG = {
    'db': DB,
    'username': USERNAME,
    'password': PASSWORD,
    'host': HOST,
    'port': PORT,
    'tags': ['foo:bar'],
}

E2E_METADATA = {
    'env_vars': {
        'IBM_DB_INSTALLER_URL': 'https://ddintegrations.blob.core.windows.net/ibm-db2/',
    },
    'start_commands': [
        'apt-get update',
        'apt-get install -y build-essential libxslt-dev',
        'pip install ibm_db==3.2.6',
    ],
}
