# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance_local_cert():
    return {
        'url': "http://www.google.com",
        # 'ssl_version': "tls_1.2"
    }


@pytest.fixture
def instance_remote_cert():
    return {
        'url': "http://www.google.com",
        # 'ssl_version': "tls_1.2"
    }
