# ABOUTME: Pytest fixtures for NiFi integration tests.
# ABOUTME: Provides dd_environment for Docker-based tests and instance fixtures.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import ssl
from copy import deepcopy
from urllib import error
from urllib.request import urlopen

import pytest

from datadog_checks.dev import WaitFor, docker_run, run_command

from . import common


def wait_for_nifi():
    """Poll the NiFi API until it responds (any HTTP status means NiFi is up)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        urlopen(f'{common.NIFI_API_URL}/flow/about', context=ctx, timeout=5)
    except error.HTTPError:
        # NiFi returns 401 on all unauthenticated requests — that's fine, it means NiFi is up.
        return
    except error.URLError:
        raise


def setup_test_flows():
    """Run the setup-flow.sh script to create test processors and connections."""
    script = os.path.join(common.HERE, 'docker', 'setup-flow.sh')
    run_command(
        ['bash', script],
        check=True,
        capture=True,
        env={
            **os.environ,
            'NIFI_API_URL': common.NIFI_API_URL,
            'NIFI_USERNAME': common.NIFI_USERNAME,
            'NIFI_PASSWORD': common.NIFI_PASSWORD,
        },
    )


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        conditions=[
            WaitFor(wait_for_nifi, attempts=60, wait=5),
            WaitFor(setup_test_flows, attempts=1, wait=0),
        ],
    ):
        yield common.CHECK_CONFIG


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)
