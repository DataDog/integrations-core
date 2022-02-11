import os

from datadog_checks.dev import get_docker_hostname
from datadog_checks.traffic_server.metrics import COUNT_METRICS, GAUGE_METRICS

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')
ROOT = os.path.dirname(os.path.dirname(HERE))
HOST = get_docker_hostname()
TRAFFIC_SERVER_VERSION = os.environ['TRAFFIC_SERVER_VERSION']

TRAFFIC_SERVER_URL = 'http://{}:8080/_stats'.format(HOST)

INSTANCE = {'traffic_server_url': TRAFFIC_SERVER_URL, 'tags': ['optional:tag1']}

EXPECTED_COUNT_METRICS = ["traffic_server.{}".format(metric_name) for metric_name in COUNT_METRICS.values()]
EXPECTED_GAUGE_METRICS = ["traffic_server.{}".format(metric_name) for metric_name in GAUGE_METRICS.values()]
