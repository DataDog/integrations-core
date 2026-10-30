# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

CHECK_NAME = 'ibm_hmc'


@pytest.fixture
def instance():
    return {
        'host': 'hmc.example.com',
        'port': 22,
        'username': 'hscroot',
        'password': 'abcdef',
    }
