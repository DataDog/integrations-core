# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.systemd import SystemdCheck

from . import common

HERE = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'systemd.yaml')
    ):
    yield {'units': ['networking.service']}


@pytest.fixture
def instance_ko():
    return {
        'units': [
				"nonexisting.service"
			],
        'collect_all_units': False
    }

@pytest.fixture
def instance():
    return {
        'units': [
				"httpd.service"
			],
        'collect_all_units': False
    }

@pytest.fixture
def instance_collect_all():
    return {
        'units': [
				"httpd.service"
			],
        'collect_all_units': True
    }


@pytest.fixture
def check():
    return SystemdCheck({"systemd", {}, {}})

