# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    # FIXME: Commenting out v12 Cloudera Docker image until confirmation this version should be supported
    
    # compose_file = os.path.join(common.HERE, 'compose', common.COMPOSE_FILE)
    # conditions = [
    #     CheckDockerLogs(
    #         identifier='cloudera', patterns=['Success! You can now log into Cloudera Manager'], attempts=180, wait=5
    #     ),
    # ]
    # with docker_run(
    #     compose_file,
    #     conditions=conditions,
    # ):
    #     yield common.INSTANCE

    compose_file = common.COMPOSE_FILE
    with docker_run(compose_file):
        yield common.INSTANCE


@pytest.fixture
def instance():
    return common.INSTANCE


@pytest.fixture(scope='session')
def cloudera_check():
    return lambda instance: ClouderaCheck('cloudera', {}, [instance])


@pytest.fixture
def api_response():
    def _response(filename):
        with open(os.path.join(common.HERE, "api_responses", f'{filename}.json'), 'r') as f:
            return json.load(f)

    return _response
