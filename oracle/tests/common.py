# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

ENV_TYPE = os.environ.get('ENV_TYPE', 'docker')
CLIENT_LIB = os.environ['CLIENT_LIB']
ORACLE_DATABASE_VERSION = os.environ['ORACLE_DATABASE_VERSION']

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

HOST = get_docker_hostname()
PORT = '1521'
USER = 'datadog'
PASSWORD = 'Oracle123'

CHECK_NAME = 'oracle'
CONTAINER_NAME = 'oracle-database'
