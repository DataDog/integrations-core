# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Any

import pytest

from .common import INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    # Lab and docker environments are added in a later task.
    yield


@pytest.fixture
def instance() -> dict[str, Any]:
    return copy.deepcopy(INSTANCE)
