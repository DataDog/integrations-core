import os
import subprocess
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope='session', autouse=True)
def spin_up_vault():
    base_command = [
        'docker-compose', '-f', os.path.join(DOCKER_DIR, 'docker-compose.yaml')
    ]
    subprocess.check_call(base_command + ['up', '-d'])
    time.sleep(5)
    yield
    subprocess.check_call(base_command + ['down'])
