# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import os


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        "avi_controller_url": "https://34.123.32.255/",
        "tls_verify": False,
        "username": "admin",
        "password": os.environ['DOCKER_AVI_PASS']
    }
