# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE, 'local'
