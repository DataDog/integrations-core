# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

HOST = get_docker_hostname()
PORT = '50000'
DB = 'datadog'
USERNAME = 'db2inst1'
PASSWORD = 'db2inst1-pwd'
DB2_VERSION = os.getenv('DB2_VERSION')

CONFIG = {
    'db': DB,
    'username': USERNAME,
    'password': PASSWORD,
    'host': HOST,
    'port': PORT,
    'tags': ['foo:bar'],
}

E2E_METADATA = {
    'start_commands': ['apt-get update', 'apt-get install -y build-essential libxslt-dev', 'pip install ibm_db']
}
