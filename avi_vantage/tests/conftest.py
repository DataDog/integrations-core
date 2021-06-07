# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import os
import mock


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def mock_client():
    with mock.patch('datadog_checks.base.utils.http.requests') as req:
        req.login_performed = False

        def post(url, *args, **kwargs):
            if not url.endswith('/login'):
                raise Exception("[MockedAvi")
                req.login_performed = True


        req.post = post
        req.get = get
        yield
@pytest.fixture
def instance():
    return {
        "avi_controller_url": "https://34.123.32.255/",
        "tls_verify": False,
        "username": "admin",
        "password": os.environ['DOCKER_AVI_PASS']
    }


