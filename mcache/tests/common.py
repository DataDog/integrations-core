# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

PORT = 11211
SERVICE_CHECK = 'memcache.can_connect'
HOST = get_docker_hostname()
USERNAME = 'testuser'
PASSWORD = 'testpass'

DOCKER_SOCKET_PATH = '/tmp/memcached.sock'
TMP_DIR = os.path.join(ROOT, "tmp")
UNIXSOCKET_PATH = os.path.join(os.path.join(TMP_DIR, "mcache"), 'memcached.sock')
