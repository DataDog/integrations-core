# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.network import Network

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE


@pytest.fixture
def check():
    return Network(common.SERVICE_CHECK_NAME, {}, {})
