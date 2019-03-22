# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.linux_proc_extras import MoreUnixCheck
from . import common


@pytest.fixture(scope="session")
def dd_environment():
    yield common.INSTANCE


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return MoreUnixCheck(common.CHECK_NAME, {}, {})
