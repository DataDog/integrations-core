# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from pkg_resources import parse_version

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTS_HELPER_DIR = os.path.join(ROOT, 'datadog_checks_tests_helper')

MYSQL_VERSION_PARSED = parse_version(os.getenv('MYSQL_VERSION'))

CHECK_NAME = 'mysql'
MASTER_CONTAINER_NAME = 'mysql-master'
SLAVE_CONTAINER_NAME = 'mysql-slave'

HOST = get_docker_hostname()
PORT = 13306
SLAVE_PORT = 13307

USER = 'dog'
PASS = 'dog'
