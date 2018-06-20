# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
import tempfile

from datadog_checks.openldap import OpenLDAP
from datadog_checks.dev import docker_run
from .common import HERE

CONTAINER_NAME = "openldap"

@pytest.fixture
def check():
    return OpenLDAP('openldap', {}, {})


@pytest.fixture(scope="session")
def openldap_server():

    host_socket_dir = os.path.realpath(tempfile.mkdtemp())
    host_socket_path = os.path.join(host_socket_dir, "ldapi")

    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        env_vars={"CONTAINER_NAME": CONTAINER_NAME, "HOST_SOCKET_DIR": host_socket_dir},
        log_patterns="slapd starting",
    ):
        os.chmod(host_socket_path, 0777)
        yield host_socket_path
