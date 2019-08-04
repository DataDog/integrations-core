# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()
PORT = '5432'
USER = 'datadog'
PASSWORD = 'datadog'
DB_NAME = 'datadog_test'


COORDINATOR_URL = 'http://localhost:8081'
BROKER_URL = 'http://localhost:8082'
