# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    yield common.get_config_stubs(".")[0]
