# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.boundary import BoundaryCheck
from datadog_checks.dev import docker_run

from . import common


@pytest.fixture(scope='session')
def dd_environment(instance):
    with docker_run(common.COMPOSE_FILE, endpoints=[common.HEALTH_ENDPOINT, common.METRIC_ENDPOINT], mount_logs=True):
        yield instance


@pytest.fixture(scope='session')
def instance():
    return {
        'health_endpoint': common.HEALTH_ENDPOINT,
        'openmetrics_endpoint': common.METRIC_ENDPOINT,
        'tags': ['foo:bar'],
    }


@pytest.fixture(scope='session')
def get_check():
    return lambda instance: BoundaryCheck('boundary', {}, [instance])
