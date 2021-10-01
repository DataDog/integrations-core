# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from sys import maxsize

import pytest
from pkg_resources import parse_version

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTS_HELPER_DIR = os.path.join(ROOT, 'datadog_checks_tests_helper')

MYSQL_VERSION_IS_LATEST = os.getenv('MYSQL_VERSION', '').endswith('latest')

if MYSQL_VERSION_IS_LATEST is False:
    MYSQL_VERSION_PARSED = parse_version(os.getenv('MYSQL_VERSION', ''))
else:
    MYSQL_VERSION_PARSED = parse_version(str(maxsize))
CHECK_NAME = 'mysql'

HOST = get_docker_hostname()
PORT = 13306
SLAVE_PORT = 13307

USER = 'dog'
PASS = 'dog'

requires_static_version = pytest.mark.skipif(
    MYSQL_VERSION_IS_LATEST, reason='Version `latest` is ever-changing, skipping'
)
