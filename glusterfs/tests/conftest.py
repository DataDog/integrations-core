# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import platform
from unittest import mock

import pytest

from datadog_checks.dev import WaitFor, run_command
from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.conditions import CheckVMLogs

ON_CI = running_on_ci()

from .common import CONFIG, INSTANCE

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()  # Reusing this as it will provide localhost on GitHub Actions
PRIMARY_VM = "gluster-node"

E2E_METADATA = {
    "agent_type": "vagrant",
    "vagrant_guest_os": "linux",
    "start_commands": [
        "sudo apt update",
        "sudo apt install -y software-properties-common",
        "sudo add-apt-repository -y ppa:gluster/glusterfs-7",
        "sudo apt install -y glusterfs-server glusterfs-client",
        "sudo systemctl start glusterd",
        "sudo systemctl enable glusterd",
        "sudo mkdir -p /gluster/brick1",
        "sudo gluster volume create volume1 172.30.1.5:/gluster/brick1 force",
        "sudo gluster volume start volume1",
        "sudo mkdir -p /gluster/brick2",
        "sudo gluster volume create volume2 172.30.1.5:/gluster/brick2 force",
        "sudo gluster volume start volume2",
    ],
}


@pytest.fixture(scope="session")
def dd_environment():
    if platform.system() == "Darwin" and not ON_CI:
        vm_config = copy.deepcopy(CONFIG)
        yield vm_config, E2E_METADATA
    else:
        raise Exception("VMs are only supported on Mac OS arm64")


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
