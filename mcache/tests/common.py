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

SOCKET = '/tmp/memcached.sock'
LOCAL_TMP_DIR = os.path.join(ROOT, "tmp")
UNIXSOCKET_DIR = os.path.join(LOCAL_TMP_DIR, "mcache")
UNIXSOCKET_PATH = os.path.join(UNIXSOCKET_DIR, 'memcached.sock')
