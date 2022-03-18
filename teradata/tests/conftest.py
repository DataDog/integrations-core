# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from .common import E2E_METADATA

TERADATA_SERVER = os.environ.get('TERADATA_SERVER')
TERADATA_DD_USER = os.environ.get('TERADATA_DD_USER')
TERADATA_DD_PW = os.environ.get('TERADATA_DD_PW')

CONFIG = {
    'server': TERADATA_SERVER,
    'username': TERADATA_DD_USER,
    'password': TERADATA_DD_PW,
    'database': 'AdventureWorksDW',
    'use_tls': False,
    'collect_res_usage': True,
}


@pytest.fixture(scope='session')
def dd_environment():
    if not TERADATA_SERVER or not TERADATA_DD_USER or not TERADATA_DD_PW:
        raise Exception(
            "Please set `TERADATA_SERVER` to a valid Teradata IP and `TERADATA_DD_USER`, `TERADATA_DD_PW` environment "
            "variables to valid Teradata User credentials."
        )
    yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(CONFIG)


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
