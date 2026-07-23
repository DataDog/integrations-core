# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from urllib import error, parse, request

import pytest

from datadog_checks.dev import docker_run

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
        payload = parse.urlencode(data).encode()
        headers = {'X-Kt-Mode': 'set', 'Content-Type': 'application/x-www-form-urlencoded'}

        for _ in range(100):
            try:
                req = request.Request(URL, data=payload, headers=headers, method='PUT')
                with request.urlopen(req):
                    pass
            except error.HTTPError as exc:
                exc.close()

            try:
                with request.urlopen(URL):
                    pass
            except error.HTTPError as exc:
                exc.close()

        yield DEFAULT_INSTANCE
