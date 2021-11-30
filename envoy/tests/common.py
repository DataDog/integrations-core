import os
import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')
DOCKER_DIR = os.path.join(HERE, 'docker')
ENVOY_LEGACY = os.getenv('ENVOY_LEGACY')

HOST = get_docker_hostname()
PORT = '8001'

URL = 'http://{}:{}'.format(HOST, PORT)
DEFAULT_INSTANCE = {'openmetrics_endpoint': '{}/stats/prometheus'.format(URL)}
requires_new_environment = pytest.mark.skipif(ENVOY_LEGACY != 'false', reason='Requires prometheus environment')
