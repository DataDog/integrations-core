# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    # Required for e2e tests to set up test environments.
    # Optional for unit tests but good practice for consistency.
    yield
