# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import os

from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    target = "varnish{}".format(os.environ["VARNISH_VERSION"].split(".")[0])

    compose_file = os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    with docker_run(compose_file, service_name=target):
        yield common.get_config_by_version(), 'local'
