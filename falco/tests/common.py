import os


from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = 8765


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)

URL = 'http://{}:{}'.format(HOST, PORT)
DEFAULT_INSTANCE = {'openmetrics_endpoint': '{}/metrics'.format(URL)}

METRICS = [
    'falco.container.info',
    'falco.container.info.count',
    'falco.container.info.duration',
    'falco.container.info.duration.count',
    'falco.container.info.duration.sum',
    'falco.container.info.duration.sum.count',
    'falco.container.info.duration.sum.count',
]





