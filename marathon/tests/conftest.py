# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os
from copy import deepcopy

import pytest

from datadog_checks.base.utils.http_testing import http_client_session  # noqa: F401

from datadog_checks.dev import docker_run
from datadog_checks.marathon import Marathon

from .common import HERE, INSTANCE_INTEGRATION


def read_fixture_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return json.loads(f.read())


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yml'), log_patterns='All services up and running.'
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return Marathon('marathon', {}, [INSTANCE_INTEGRATION])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def apps():
    return read_fixture_file('apps.json')


@pytest.fixture
def deployments():
    return read_fixture_file('deployments.json')


@pytest.fixture
def queue():
    return read_fixture_file('queue.json')


@pytest.fixture
def groups():
    return read_fixture_file('groups.json')
