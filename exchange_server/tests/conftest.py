# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.exchange_server import ExchangeCheck

from .common import INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE, {'docker_platform': 'windows'}


@pytest.fixture
def check():
    return lambda instance: ExchangeCheck('exchange_server', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
