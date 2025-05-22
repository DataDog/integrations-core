# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import platform
from unittest import mock

import pytest

from datadog_checks.dev import WaitFor, run_command, vm_run
from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.conditions import CheckVMLogs

ON_CI = running_on_ci()

from .common import CONFIG, INSTANCE

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()  # Reusing this as it will provide localhost on GitHub Actions
PRIMARY_VM = "gluster-node-1"
SECONDARY_VM = "gluster-node-2"

E2E_METADATA = {
    "start_commands": [
    ],
}


@pytest.fixture(scope="session")
def dd_environment():
    if platform.system() == "Darwin" and not ON_CI:
        vagrant_file = os.path.join(HERE, "vm", "Vagrantfile")

        log_patterns = ["GlusterFS started"]
        vm_conditions = []
        vm_conditions.append(CheckVMLogs(PRIMARY_VM, log_patterns))
        vm_conditions.append(CheckVMLogs(SECONDARY_VM, log_patterns))
        vm_conditions.append(WaitFor(setup_gluster_cluster))

        with vm_run(
            vm_definition=vagrant_file,
            conditions=vm_conditions,
            down=teardown_gluster_cluster,
            attempts=1,
            attempts_wait=15,
            primary_vm=PRIMARY_VM,
        ):
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


def setup_gluster_cluster():
    """Setup GlusterFS cluster on VMs"""
    # # Get the IP addresses of both VMs
    # if platform.system() == "Darwin":
    #     # On macOS use Vagrant commands
    #     vagrant_dir = os.path.join(HERE, "vm")

    #     # Change to vagrant directory
    #     original_dir = os.getcwd()
    #     os.chdir(vagrant_dir)

    #     try:
    #         # Get node1 IP - specify VM name
    #         cmd1 = ["vagrant", "ssh", PRIMARY_VM, "-c", "hostname -I | cut -d' ' -f2"]
    #         node1_ip = run_command(cmd1, capture="out", check=True).stdout.strip()

    #         # Get node2 IP - specify VM name
    #         cmd2 = ["vagrant", "ssh", SECONDARY_VM, "-c", "hostname -I | cut -d' ' -f2"]
    #         node2_ip = run_command(cmd2, capture="out", check=True).stdout.strip()

    #         # Add hosts entries - specify VM name
    #         run_command(
    #             ["vagrant", "ssh", PRIMARY_VM, "-c", f"echo '{node2_ip} {SECONDARY_VM}' | sudo tee -a /etc/hosts"],
    #             capture=True,
    #             check=True,
    #         )
    #         run_command(
    #             ["vagrant", "ssh", SECONDARY_VM, "-c", f"echo '{node1_ip} {PRIMARY_VM}' | sudo tee -a /etc/hosts"],
    #             capture=True,
    #             check=True,
    #         )

    #         # Setup the GlusterFS cluster - specify VM name
    #         commands = [
    #             f"sudo gluster peer probe {SECONDARY_VM}",
    #             f"sudo gluster volume create gv0 replica 2 {PRIMARY_VM}:/export-test {SECONDARY_VM}:/export-test force",
    #             "sudo gluster volume start gv0",
    #         ]

    #         for command in commands:
    #             run_command(["vagrant", "ssh", PRIMARY_VM, "-c", command], capture=True, check=True)

    #         # Verify the cluster is running
    #         # Check volume status - specify VM name
    #         status_cmd = ["vagrant", "ssh", PRIMARY_VM, "-c", "sudo gluster volume status"]
    #         status_output = run_command(status_cmd, capture="out", check=True).stdout

    #         # If "Status: Started" is in the output, the volume is running
    #         return "Status: Started" in status_output
    #     finally:
    #         # Change back to original directory
    #         os.chdir(original_dir)
    # else:
    #     # For GitHub Actions, the setup is handled by the script
    #     return True


def teardown_gluster_cluster():
    """Teardown GlusterFS cluster on VMs"""
    if platform.system() == "Darwin":
        vagrant_dir = os.path.join(HERE, "vm")

        # Change to vagrant directory
        original_dir = os.getcwd()
        os.chdir(vagrant_dir)

        try:
            pass
            # Stop and delete the GlusterFS volume - specify VM name
            # try:
            #     run_command(
            #         ["vagrant", "ssh", PRIMARY_VM, "-c", "sudo gluster volume stop gv0 --mode=script"],
            #         capture=True,
            #         check=False,
            #     )
            #     run_command(
            #         ["vagrant", "ssh", PRIMARY_VM, "-c", "sudo gluster volume delete gv0 --mode=script"],
            #         capture=True,
            #         check=False,
            #     )
            # except Exception:
            #     # Ignore errors during teardown
            #     pass
        finally:
            # Change back to original directory
            os.chdir(original_dir)
    else:
        # GitHub Actions cleanup is handled in the teardown function
        pass
