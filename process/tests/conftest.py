# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.process import ProcessCheck

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    yield common.instance


@pytest.fixture
def check():
    return ProcessCheck(common.CHECK_NAME, {}, {})
