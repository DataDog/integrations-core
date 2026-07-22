# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from .common import INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    # This integration talks to the Genesys Cloud SaaS API and has no
    # self-hostable dependency, so there is no e2e environment to start. A
    # no-op fixture keeps `ddev env test` from erroring on a missing
    # `dd_environment` while it collects zero e2e tests.
    yield


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)
