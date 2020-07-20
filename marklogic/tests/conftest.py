# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import run_command

from .common import CHECK_CONFIG, HERE, API_URL, USERNAME, PASSWORD


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yml')
    with docker_run(
            compose_file=compose_file,
            log_patterns=[r'Detected quorum \(2 online'],
    ):
        # From https://docs.marklogic.com/10.0/guide/admin-api/cluster
        run_command([
            'curl',
            '-X',
            'POST',
            '-H',
            '"Content-type: application/x-www-form-urlencoded"',
            '--data',
            '"admin-username=admin"',
            '--data',
            '"admin-password=admin"',
            'http://localhost:8001/admin/v1/instance-admin',
        ])
        yield CHECK_CONFIG
