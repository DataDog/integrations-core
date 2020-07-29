# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, Dict

import yaml

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

INSTANCE_FILTERS = {
    'url': API_URL,
    'username': USERNAME,
    'password': PASSWORD,
    'auth_type': 'digest',
    'resource_filters': [
        {'resource_type': 'forest', 'pattern': '^S[a-z]*'},  # Match Security and Schemas
        {'resource_type': 'forest', 'pattern': '^Sch*', 'include': False},  # Unmatch Schemas
        {'resource_type': 'server', 'pattern': 'Admin', 'group': 'Default'},
    ],
}


CHECK_CONFIG = {
    'init_config': {},
    'instances': [INSTANCE],
}


def read_fixture_file(fname):
    # type: (str) -> Dict[str, Any]
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return yaml.safe_load(f.read())
