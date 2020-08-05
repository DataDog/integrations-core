# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, Dict, Generator

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

from .common import ADMIN_PASSWORD, ADMIN_USERNAME, API_URL, CHECK_CONFIG, HERE, PASSWORD, USERNAME


@pytest.fixture(scope="session")
def dd_environment():
    # type: () -> Generator[Dict[str, Any], None, None]

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yml')
    with docker_run(
        compose_file=compose_file,
        conditions=[
            CheckDockerLogs(compose_file, r'Info:'),
            WaitFor(setup_admin_user, attempts=20),
            WaitFor(setup_datadog_user, attempts=10),
            WaitFor(joining_cluster, attempts=10),
            CheckDockerLogs(compose_file, r'Detected quorum'),
        ],
    ):
        yield CHECK_CONFIG


def joining_cluster():
    # type: () -> None

    # See https://www.marklogic.com/blog/docker-marklogic-initialization/
    # Get the joining node configuration
    r_joining_config = requests.get(
        'http://localhost:18001/admin/v1/server-config',
        headers={'Accept': 'application/xml'},
        auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
    )
    r_joining_config.raise_for_status()

    # Update the config on the bootstrap side
    r_bootstrap = requests.post(
        'http://localhost:8001/admin/v1/cluster-config',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
        params={'server-config': r_joining_config.content, 'group': 'Default'},
    )
    r_bootstrap.raise_for_status()

    # Make the node join the cluster
    r_join = requests.post(
        'http://localhost:18001/admin/v1/cluster-config',
        headers={'Content-Type': 'application/zip'},
        auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
        data=r_bootstrap.content,
    )
    r_join.raise_for_status()


def setup_admin_user():
    # type: () -> None
    # From https://docs.marklogic.com/10.0/guide/admin-api/cluster
    # Reset admin user password (usefull for cluster setup)

    ret = True

    try:
        r = requests.get(
            '{}/manage/v2'.format(API_URL), auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD)
        )
        r.raise_for_status()
    except Exception:
        requests.post(
            'http://localhost:8001/admin/v1/instance-admin',
            data={
                "admin-username": ADMIN_USERNAME,
                "admin-password": ADMIN_PASSWORD,
                "realm": "public",
            },
            headers={"Content-type": "application/x-www-form-urlencoded"},
        )
        ret = False

    try:
        r = requests.get(
            'http://localhost:18002/manage/v2', auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD)
        )
        r.raise_for_status()
    except Exception:
        requests.post(
            'http://localhost:18001/admin/v1/instance-admin',
            data={
                "admin-username": ADMIN_USERNAME,
                "admin-password": ADMIN_PASSWORD,
                "realm": "public",
            },
            headers={"Content-type": "application/x-www-form-urlencoded"},
        )
        ret = False
    return ret


def setup_datadog_user():
    # type: () -> None
    # Create datadog user with the admin account
    r = requests.post(
        '{}/manage/v2/users'.format(API_URL),
        headers={'Content-Type': 'application/json'},
        data='{{"user-name": "{}", "password": "{}", "roles": {{"role": "manage-admin"}}}}'.format(USERNAME, PASSWORD),
        auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
    )

    r.raise_for_status()
