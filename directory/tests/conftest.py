# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.directory import DirectoryCheck

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    yield common.get_config_stubs(".")[0]


@pytest.fixture
def check():
    return DirectoryCheck(common.CHECK_NAME)
