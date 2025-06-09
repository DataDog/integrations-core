import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = 8765


URL = 'http://{}:{}'.format(HOST, PORT)
INSTANCE = {'openmetrics_endpoint': '{}/metrics'.format(URL)}

METRICS = [
    'falco.container.info',
    'falco.container.info.count',
    'falco.container.info.duration',
    'falco.container.info.duration.count',
    'falco.container.info.duration.sum',
    'falco.container.info.duration.sum.count',
    'falco.container.info.duration.sum.count',
]
