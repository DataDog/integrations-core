import os
import pytest
from datadog_checks.dev import docker_run
from .common import INSTANCE, COMPOSE
from copy import deepcopy


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(COMPOSE, 'docker-compose.yaml')
    
    with docker_run(
        compose_file,
        log_patterns=[r'.*'],
        build=True,
        service_name='silverstripe',
        sleep=30,
    ):
        instance = INSTANCE.copy()
        yield instance
    
@pytest.fixture
def instance():
    return deepcopy(INSTANCE)
