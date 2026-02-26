# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common


@pytest.fixture
def postgres_instance():
    return deepcopy(common.POSTGRES_INSTANCE)


@pytest.fixture
def multi_query_instance():
    return deepcopy(common.MULTI_QUERY_INSTANCE)
