# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

TERADATA_SERVER = os.environ.get('TERADATA_SERVER')
TERADATA_DD_USER = os.environ.get('TERADATA_DD_USER')
TERADATA_DD_PW = os.environ.get('TERADATA_DD_PW')

CONFIG = {
    'server': 'localhost',
    'username': 'datadog',
    'password': 'td_datadog',
    'database': 'AdventureWorksDW',
    'use_tls': False,
    'collect_res_usage': True,
}

E2E_CONFIG = {
    'server': TERADATA_SERVER,
    'username': TERADATA_DD_USER,
    'password': TERADATA_DD_PW,
    'database': 'AdventureWorksDW',
    'use_tls': False,
    'collect_res_usage': True,
}


@pytest.fixture(scope='session')
def dd_environment():
    yield E2E_CONFIG


@pytest.fixture
def instance():
    return deepcopy(E2E_CONFIG)


@pytest.fixture
def instance_res_usage():
    instance = deepcopy(CONFIG)
    instance['collect_res_usage'] = True
    return instance


@pytest.fixture
def bad_instance():
    bad_config = deepcopy(CONFIG)
    bad_config['server'] = 'fakeserver.com'
    return bad_config
