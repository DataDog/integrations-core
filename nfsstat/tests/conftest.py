# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from subprocess import check_output

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

from .common import COMPOSE_FILE, CONFIG, E2E_METADATA

NFS_CLIENT_CONTAINER_NAME = 'nfs-client'


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        COMPOSE_FILE,
        conditions=[CheckDockerLogs(NFS_CLIENT_CONTAINER_NAME, 'NFS Client ready.'), WaitFor(wait_for_nfsiostat)],
    ):
        yield CONFIG, E2E_METADATA


def wait_for_nfsiostat():
    output = check_output(CONFIG["init_config"]["nfsiostat_path"].split())
    print(output)

    return "nfs-server:/ mounted on /test1:" in output
