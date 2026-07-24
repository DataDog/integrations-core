# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.http import http_get, http_put

from .common import DEFAULT_INSTANCE, HERE, URL


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up a kyototycoon docker image
    """

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'compose_kyototycoon.yaml'),
        endpoints='{}/rpc/report'.format(URL),
        mount_logs=True,
    ):
        # Generate a test database
        data = {'dddd': 'dddd'}
        headers = {'X-Kt-Mode': 'set'}

        for _ in range(100):
            http_put(URL, data=data, headers=headers)
            http_get(URL)

        yield DEFAULT_INSTANCE
