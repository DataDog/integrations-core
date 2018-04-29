import os
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


@pytest.fixture(scope='session', autouse=True)
def spin_up_envoy():
    flavor = os.getenv('FLAVOR', 'default')
    base_command = [
        'docker-compose', '-f', os.path.join(DOCKER_DIR, flavor, 'docker-compose.yaml')
    ]
    subprocess.check_call(base_command + ['up', '-d', '--build'])
    yield
    subprocess.check_call(base_command + ['down'])
