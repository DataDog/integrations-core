import logging

from datadog_checks.dev import get_docker_hostname, get_here

log = logging.getLogger('test_kong')

HERE = get_here()

CHECK_NAME = 'kong'
HOST = get_docker_hostname()
PORT = 8001

METRICS_URL = 'http://{}:{}/metrics'.format(HOST, PORT)
STATUS_URL = 'http://{}:{}/status/'.format(HOST, PORT)

instance_1 = {'kong_status_url': STATUS_URL, 'tags': ['first_instance']}

instance_2 = {'kong_status_url': STATUS_URL, 'tags': ['second_instance']}

openmetrics_instance = {'openmetrics_endpoint': METRICS_URL, 'tags': ['openmetrics_instance']}

CONFIG_STUBS = [instance_1, instance_2]
