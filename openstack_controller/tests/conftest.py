# C Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License see LICENSE
import pytest


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator
