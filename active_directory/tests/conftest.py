# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    # This is a required fixture for e2e tests, but good practice to have.
    # For unit tests, it doesn't do anything.
    yield
