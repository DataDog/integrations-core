# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.utils import ON_LINUX, ON_WINDOWS

HERE = os.path.dirname(os.path.abspath(__file__))

PORT = 11211
SERVICE_CHECK = 'memcache.can_connect'
HOST = get_docker_hostname()
USERNAME = 'testuser'
PASSWORD = 'testpass'

DOCKER_SOCKET_DIR = '/tmp'
DOCKER_SOCKET_PATH = '/tmp/memcached.sock'

platform_supports_sockets = ON_LINUX
requires_socket_support = pytest.mark.skipif(
    not platform_supports_sockets, reason='Windows sockets are not file handles'
)
requires_unix_utils = pytest.mark.skipif(ON_WINDOWS, reason='Windows does not have access to unix programs')
