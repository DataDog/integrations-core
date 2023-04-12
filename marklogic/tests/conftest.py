# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, Dict, Generator  # noqa: F401

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

from .common import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    API_URL,
    CHECK_CONFIG,
    HERE,
    MANAGE_ADMIN_USERNAME,
    MANAGE_USER_USERNAME,
    PASSWORD,
)


@pytest.fixture(scope="session")
def dd_environment():
    # type: () -> Generator[Dict[str, Any], None, None]

    # Standalone
    compose_file = os.path.join(HERE, 'compose', 'standalone/docker-compose.yml')
    with docker_run(
        compose_file=compose_file,
        conditions=[
            CheckDockerLogs(compose_file, r'Deleted'),
            WaitFor(setup_admin_user),
            WaitFor(setup_datadog_users),
        ],
    ):
        yield CHECK_CONFIG


def setup_admin_user():
    # type: () -> None
    # From https://docs.marklogic.com/10.0/guide/admin-api/cluster
    # Reset admin user password (usefull for cluster setup)
    requests.post(
        'http://localhost:8001/admin/v1/instance-admin',
        data={
            "admin-username": ADMIN_USERNAME,
            "admin-password": ADMIN_PASSWORD,
            "wallet-password": ADMIN_PASSWORD,
            "realm": "public",
        },
        headers={"Content-type": "application/x-www-form-urlencoded"},
    )

    r = requests.get('{}/manage/v2'.format(API_URL), auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD))

    r.raise_for_status()


def setup_datadog_users():
    # type: () -> None
    # Create datadog users with the admin account
    r = requests.post(
        '{}/manage/v2/users'.format(API_URL),
        headers={'Content-Type': 'application/json'},
        data='{{"user-name": "{}", "password": "{}", "roles": {{"role": "manage-user"}}}}'.format(
            MANAGE_USER_USERNAME, PASSWORD
        ),
        auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
    )

    r.raise_for_status()

    r = requests.post(
        '{}/manage/v2/users'.format(API_URL),
        headers={'Content-Type': 'application/json'},
        data='{{"user-name": "{}", "password": "{}", "roles": {{"role": "manage-admin"}}}}'.format(
            MANAGE_ADMIN_USERNAME, PASSWORD
        ),
        auth=requests.auth.HTTPDigestAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
    )

    r.raise_for_status()
