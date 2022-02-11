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

# metrics that are not available in the e2e environment
NON_E2E_METRICS = [
    'process.http.origin_server_total_request_bytes',
    'process.origin_server_total_bytes',
    'process.user_agent_total_bytes',
    'process.cache.total_hits_bytes',
    'process.http.origin_server_total_response_bytes',
    'process.http.user_agent_total_request_bytes',
    'process.cache.total_misses_bytes',
    'process.cache.total_bytes',
    'process.cache.total_misses',
    'process.http.user_agent_total_response_bytes',
    'process.cache.total_hits',
    'process.cache.total_requests',
    'process.current_server_connections',
    'node.proxy_running',
]

EXPECTED_COUNT_METRICS = [
    "traffic_server.{}".format(metric_name)
    for metric_name in COUNT_METRICS.values()
    if metric_name not in NON_E2E_METRICS
]
EXPECTED_GAUGE_METRICS = [
    "traffic_server.{}".format(metric_name)
    for metric_name in GAUGE_METRICS.values()
    if metric_name not in NON_E2E_METRICS
]
