# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'powerdns.yaml'),
        env_vars={'POWERDNS_CONFIG': os.path.join(common.HERE, 'compose', 'recursor.conf')},
        log_patterns="Listening for HTTP requests",
    ):
        yield common.CONFIG if common._get_pdns_version() == 3 else common.CONFIG_V4
