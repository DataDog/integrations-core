# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import load_jmx_config


@pytest.fixture(scope='session')
def dd_environment():
    yield load_jmx_config()


@pytest.fixture
def instance():

    return {}
