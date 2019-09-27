# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = '23790'
V3_PREVIEW = os.getenv('V3_PREVIEW') == 'true'
URL = 'http://{}:{}'.format(HOST, PORT)

STORE_METRICS = [
    'compareanddelete.fail',
    'compareanddelete.success',
    'compareandswap.fail',
    'compareandswap.success',
    'create.fail',
    'create.success',
    'delete.fail',
    'delete.success',
    'expire.count',
    'gets.fail',
    'gets.success',
    'sets.fail',
    'sets.success',
    'update.fail',
    'update.success',
    'watchers',
]
