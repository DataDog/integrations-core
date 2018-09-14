# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.oracle import Oracle


HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_NAME = "oracle"


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return Oracle(CHECK_NAME, {}, {})


@pytest.fixture
def instance():
    return {
        'server': 'localhost:1521',
        'user': 'system',
        'password': 'oracle',
        'service_name': 'xe',
        'tags': ['optional:tag1']
    }
