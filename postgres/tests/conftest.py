# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Simplified conftest for dummy tests - no postgres environment setup needed.
"""
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    """
    No environment setup needed for dummy tests.
    """
    yield {}, {}
