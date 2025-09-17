# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

AWS_INSTANCE = {
    "pc_ip": "nutanix-prism-central-nlb-7160b14f9d5c530e.elb.us-east-1.amazonaws.com",
    "pc_port": 9440,
    "username": "admin",
    "password": "uyp2ZFW9qat4dxn-rza",
    "tls_verify": False,
}


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {}


@pytest.fixture
def aws_instance():
    return AWS_INSTANCE
