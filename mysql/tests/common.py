# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from sys import maxsize

import pytest
from packaging.version import parse as parse_version

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTS_HELPER_DIR = os.path.join(ROOT, 'datadog_checks_tests_helper')

MYSQL_REPLICATION = os.getenv('MYSQL_REPLICATION')
MYSQL_VERSION_IS_LATEST = os.getenv('MYSQL_VERSION', '').endswith('latest')

if MYSQL_VERSION_IS_LATEST is False:
    MYSQL_VERSION_PARSED = parse_version(os.getenv('MYSQL_VERSION', '').split('-')[0])
else:
    MYSQL_VERSION_PARSED = parse_version(str(maxsize))
CHECK_NAME = 'mysql'

# adding flavor to differentiate mariadb from mysql
MYSQL_FLAVOR = os.getenv('MYSQL_FLAVOR', '')

HOST = get_docker_hostname()
PORT = 13306
SLAVE_PORT = 13307
PORTS_GROUP = [13306, 13307, 13308]

USER = 'dog'
PASS = 'dog'

requires_static_version = pytest.mark.skipif(
    MYSQL_VERSION_IS_LATEST, reason='Version `latest` is ever-changing, skipping'
)
requires_classic_replication = pytest.mark.skipif(
    MYSQL_REPLICATION != 'classic', reason='Classic replication not active, skipping'
)
