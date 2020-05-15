# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from subprocess import check_output

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from datadog_checks.base.utils.subprocess_output import get_subprocess_output


from .common import COMPOSE_FILE, CONFIG, E2E_METADATA


NFS_CLIENT_CONTAINER_NAME = 'nfs-client'

@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(COMPOSE_FILE, conditions=[
        CheckDockerLogs(NFS_CLIENT_CONTAINER_NAME, 'NFS Client ready.'),
        WaitFor(wait_for_nfsiostat),
    ]):
        yield CONFIG, E2E_METADATA

def wait_for_nfsiostat():
    output = check_output(CONFIG["init_config"]["nfsiostat_path"].split())

    print()
    return output != 'No NFS mount points were found'
