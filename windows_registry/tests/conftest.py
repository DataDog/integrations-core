# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from tests.common import INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE, {'docker_platform': 'windows'}
