# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.base.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
PORT = 8002
API_URL = "http://{}:{}".format(HOST, PORT)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
USERNAME = 'datadog'
PASSWORD = 'datadog'

INSTANCE = {
    'url': API_URL,
    'username': USERNAME,
    'password': PASSWORD,
    'auth_type': 'digest',
    'tags': ['foo:bar'],
}


CHECK_CONFIG = {
    'init_config': {},
    'instances': [INSTANCE],
}
