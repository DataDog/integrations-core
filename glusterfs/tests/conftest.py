# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from unittest import mock

import pytest

from .common import CONFIG, INSTANCE

HERE = os.path.dirname(os.path.abspath(__file__))

E2E_METADATA = {
    "agent_type": "vagrant",
    "vagrant_guest_os": "linux",
    "start_commands": [
        "sudo apt update",
        "sudo apt install -y software-properties-common",
        "sudo add-apt-repository ppa:gluster/glusterfs-11 -y",
        "sudo apt-get update",
        "sudo apt-get install -y glusterfs-server=11.1* glusterfs-client=11.1*",
        "sudo systemctl start glusterd",
        "sudo systemctl enable glusterd",
        "sudo mkdir -p /gluster/brick1",
        "sudo gluster volume create volume1 172.30.1.5:/gluster/brick1 force",
        "sudo gluster volume start volume1",
        "sudo mkdir -p /gluster/brick2",
        "sudo gluster volume create volume2 172.30.1.5:/gluster/brick2 force",
        "sudo gluster volume start volume2",
    ],
    "vagrant_sudoers_config": "dd-agent ALL=(ALL) NOPASSWD: /usr/sbin/gluster\ndd-agent ALL=(ALL) NOPASSWD: /sbin/gluster",  # noqa: E501
}


@pytest.fixture(scope="session")
def dd_environment():
    vm_config = copy.deepcopy(CONFIG)
    yield vm_config, E2E_METADATA


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def config():
    return copy.deepcopy(CONFIG)


@pytest.fixture()
def mock_gstatus_data():
    f_name = os.path.join(os.path.dirname(__file__), "fixtures", "gstatus.txt")
    with open(f_name) as f:
        data = f.read()

    with mock.patch("datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_data", return_value=data):
        yield
