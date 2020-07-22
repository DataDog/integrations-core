# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor, run_command

from .common import ADMIN_PASSWORD, ADMIN_USERNAME, API_URL, CHECK_CONFIG, HERE, PASSWORD, USERNAME


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yml')
    with docker_run(
        compose_file=compose_file,
        conditions=[CheckDockerLogs(compose_file, r'Detected quorum \(2 online'), WaitFor(setup_admin_user)],
    ):
        # setup_datadog_user()
        yield CHECK_CONFIG


def setup_admin_user():
    # From https://docs.marklogic.com/10.0/guide/admin-api/cluster
    # Set admin user password
    run_command(
        [
            'curl',
            '-i',
            '-X',
            'POST',
            '-H',
            '"Content-type: application/x-www-form-urlencoded"',
            '--data',
            '"admin-username={}"'.format(ADMIN_USERNAME),
            '--data',
            '"admin-password={}"'.format(ADMIN_PASSWORD),
            'http://localhost:8001/admin/v1/instance-admin',
        ],
        check=True,
    )
    result = run_command(
        [
            'curl',
            '-i',
            '--anyauth',
            '--user',
            '{}:{}'.format(ADMIN_USERNAME, ADMIN_PASSWORD),
            '{}/manage/v2'.format(API_URL),
        ]
    )

    return '401 Unauthorized' not in result.stdout


def setup_datadog_user():
    # body = {
    #     "user-name": USERNAME,
    #     "password": PASSWORD,
    #     "roles": { "role": "manage-user" },
    # }
    body = (
        '<root><password>datadog</password><roles><role>manage-user</role></roles><user-name>datadog</user-name></root>'
    )
    command = (
        [
            'curl',
            '-i',
            '-X',
            'POST',
            '--anyauth',
            '--user',
            '{}:{}'.format(ADMIN_USERNAME, ADMIN_PASSWORD),
            '-H',
            '"Content-Type: application/xml"',
            '-d',
            '"{}"'.format(body),
            '{}/manage/v2/users?format=xml'.format(API_URL),
        ],
    )

    # Create datadog user with the admin account
    result = run_command(command, check=True,)
