import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 5556


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:test'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = [ 
    'appliance.cpu.usage.percent', 
    'appliance.disk',
    'controller.client.authentication'
]

METRICS_MOCK = [f'appgate.{m}' for m in METRICS_MOCK]
