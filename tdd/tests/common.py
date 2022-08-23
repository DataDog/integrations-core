# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 27017
PORT_ERROR = 33333

COMPOSE_FILE = os.getenv('COMPOSE_FILE')
IS_STANDALONE = COMPOSE_FILE == 'mongo-standalone.yaml'

standalone = pytest.mark.skipif(not IS_STANDALONE, reason='Test only valid for standalone mongo')

MONGODB_VERSION = os.environ['MONGO_VERSION']

ROOT = os.path.dirname(os.path.dirname(HERE))

INSTANCE_BASIC = {'hosts': ['{}:{}'.format(HOST, PORT)]}
