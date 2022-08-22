import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 27017

COMPOSE_FILE = os.getenv('COMPOSE_FILE')
IS_STANDALONE = COMPOSE_FILE == 'mongo-standalone.yaml'

standalone = pytest.mark.skipif(not IS_STANDALONE, reason='Test only valid for standalone mongo')

INSTANCE_BASIC = {'hosts': ['{}:{}'.format(HOST, PORT)]}
