# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
SERVER = get_docker_hostname()
PORT = 39017

CONFIG = {'server': SERVER, 'port': PORT, 'username': 'datadog', 'password': 'Datadog9000'}
ADMIN_CONFIG = {'server': SERVER, 'port': PORT, 'username': 'system', 'password': 'Admin1337'}

USING_HDBCLI = os.environ.get('USE_PROPRIETARY_LIBRARY') == 'true'

E2E_METADATA = {}
if os.environ.get('USE_PROPRIETARY_LIBRARY') == 'true':
    E2E_METADATA['start_commands'] = ['pip install hdbcli==2.10.15']

requires_legacy_library = pytest.mark.skipif(USING_HDBCLI, reason='Requires pyhdb')
requires_proprietary_library = pytest.mark.skipif(not USING_HDBCLI, reason='Requires hdbcli')
