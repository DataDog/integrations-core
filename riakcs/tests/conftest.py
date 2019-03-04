# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import os

import pytest
import mock

from datadog_checks.riakcs import RiakCs
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(common.HERE, "compose", "docker-compose.yaml")
    with docker_run(
        compose_file=compose_file,
        conditions=[CheckDockerLogs("dd-test-riakcs", "INFO success: riak-cs entered RUNNING state", attempts=240)],
    ):
        yield common.generate_config_with_creds()


@pytest.fixture
def mocked_check():
    check = RiakCs(common.CHECK_NAME, None, {}, [{}])

    file_contents = common.read_fixture('riakcs_in.json')

    check._get_stats = mock.Mock(return_value=check.load_json(file_contents))
    return check


@pytest.fixture
def instance():
    return copy.deepcopy(common.CONFIG)


@pytest.fixture
def instance21():
    return copy.deepcopy(common.CONFIG_21)


@pytest.fixture
def check():
    return RiakCs(common.CHECK_NAME, None, {}, [{}])


@pytest.fixture
def mocked_check21():
    check = RiakCs(common.CHECK_NAME, None, {}, [{}])

    file_contents = common.read_fixture('riakcs21_in.json')

    check._get_stats = mock.Mock(return_value=check.load_json(file_contents))
    return check
