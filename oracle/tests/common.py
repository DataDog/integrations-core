# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()

CLIENT_LIB = os.environ['CLIENT_LIB']
ORACLE_DATABASE_VERSION = os.environ['ORACLE_DATABASE_VERSION']
ENABLE_TCPS = os.getenv("ENABLE_TCPS", False)
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

HOST = get_docker_hostname()
PORT = '1521'
TCPS_PORT = '2484'
USER = 'datadog'
PASSWORD = 'Oracle123'

CHECK_NAME = 'oracle'
CONTAINER_NAME = 'oracle-database'


def mock_bad_executor():
    def executor(_):
        raise

    return executor
