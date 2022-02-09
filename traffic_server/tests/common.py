import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')
ROOT = os.path.dirname(os.path.dirname(HERE))
HOST = get_docker_hostname()
#TRAFFIC_SERVER_VERSION = os.environ['TRAFFIC_SERVER_VERSION']

TRAFFIC_SERVER_URL = 'http://{}:8080/_stats'.format(HOST)

INSTANCE = {'traffic_server_url': TRAFFIC_SERVER_URL, 'tags': ['optional:tag1']}
