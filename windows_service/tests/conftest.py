# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.windows_service import WindowsService

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE_BASIC, {'docker_platform': 'windows'}


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
def instance_basic_dict():
    return deepcopy(common.INSTANCE_BASIC_DICT)


@pytest.fixture
def instance_basic_disable_service_tag():
    return deepcopy(common.INSTANCE_BASIC_DISABLE_SERVICE_TAG)


@pytest.fixture
def instance_wildcard():
    return deepcopy(common.INSTANCE_WILDCARD)


@pytest.fixture
def instance_wildcard_dict():
    return deepcopy(common.INSTANCE_WILDCARD_DICT)


@pytest.fixture
def instance_all():
    return deepcopy(common.INSTANCE_ALL)


@pytest.fixture
def instance_startup_type_filter():
    return deepcopy(common.INSTANCE_STARTUP_TYPE_FILTER)


@pytest.fixture
def instance_trigger_start():
    return deepcopy(common.INSTANCE_TRIGGER_START)


@pytest.fixture
def instance_name_regex_prefix():
    return deepcopy(common.INSTANCE_PREFIX_MATCH)
