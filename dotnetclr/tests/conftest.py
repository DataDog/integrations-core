# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.dotnetclr.check import DotnetclrCheckV2

from .common import INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE, {
        'docker_platform': 'windows',
    }


@pytest.fixture
def check():
    return lambda instance: DotnetclrCheckV2('dotnetclr', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
