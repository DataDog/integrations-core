# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# 3rd party
import pytest


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator
