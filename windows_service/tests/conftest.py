# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.windows_service import WindowsService

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE_BASIC, 'local'


@pytest.fixture
def check():
    return lambda instance: WindowsService('windows_service', {}, [instance])


@pytest.fixture
def instance_bad_config():
    return {}


@pytest.fixture
def instance_basic():
    return deepcopy(common.INSTANCE_BASIC)


@pytest.fixture
def instance_basic_disable_service_tag():
    return deepcopy(common.INSTANCE_BASIC_DISABLE_SERVICE_TAG)


@pytest.fixture
def instance_wildcard():
    return deepcopy(common.INSTANCE_WILDCARD)


@pytest.fixture
def instance_all():
    return deepcopy(common.INSTANCE_ALL)
