# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.testing.selection import EnvironmentCatalog
from tests.helpers.environments import make_catalog


@pytest.fixture
def catalog() -> EnvironmentCatalog:
    return make_catalog(
        {
            'a': {'python': '3.13'},
            'b': {'python': '3.12'},
            'windows': {'python': '3.13', 'platforms': ['windows']},
            'disabled': {'python': '3.13', 'test-env': False, 'e2e-env': False},
            'latest': {'python': '3.13', 'latest-env': True},
            'bench': {'python': '3.13', 'benchmark-env': True},
        },
        {'default': ['a', 'b', 'windows', 'disabled']},
    )
