# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from .common import E2E_METADATA

DBCNAME = os.environ.get('DBCNAME')

CONFIG = {
    'host': 'localhost',
    'connection_string': 'DRIVER=Teradata Database ODBC Driver 17.10;DBCName={};UID=dbc;PWD=datad0g123;'.format(
        DBCNAME
    ),
}


@pytest.fixture(scope='session')
def dd_environment():
    yield CONFIG, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(CONFIG)
