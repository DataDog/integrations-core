# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common
from datadog_checks.ibm_was import IbmWasCheck


@pytest.fixture(scope="session")
def instance():
    return common.INSTANCE


@pytest.fixture()
def check():
    return IbmWasCheck('ibm_was', {}, {})
