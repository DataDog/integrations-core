# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import MINIMAL_INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield MINIMAL_INSTANCE, {
        'docker_platform': 'windows',
    }
