# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

INSTANCE = {'aci_url': 'http://localhost', 'username': 'admin', 'pwd': 'admin'}


@pytest.fixture(scope="session")
def dd_environment():
    yield deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
