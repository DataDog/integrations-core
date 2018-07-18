# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, temp_dir
from datadog_checks.dev.utils import create_file
from datadog_checks.openldap import OpenLDAP
from .common import HERE


@pytest.fixture
def check():
    return OpenLDAP('openldap', {}, {})


@pytest.fixture(scope="session")
def openldap_server():
    with temp_dir() as d:
        host_socket_path = os.path.join(d, "ldapi")
        os.chmod(d, 0o777)
        create_file(host_socket_path)
        os.chmod(host_socket_path, 0o777)

        with docker_run(
            compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
            env_vars={"HOST_SOCKET_DIR": d},
            log_patterns="slapd starting",
        ):
            yield host_socket_path
