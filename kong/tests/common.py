import logging

from datadog_checks.dev import get_docker_hostname, get_here

log = logging.getLogger('test_kong')

HERE = get_here()

CHECK_NAME = 'kong'
HOST = get_docker_hostname()
PORT = 8001

STATUS_URL = 'http://{}:{}/status/'.format(HOST, PORT)

instance_1 = {'kong_status_url': STATUS_URL, 'tags': ['first_instance']}

instance_2 = {'kong_status_url': STATUS_URL, 'tags': ['second_instance']}

CONFIG_STUBS = [instance_1, instance_2]

BAD_CONFIG = {'kong_status_url': 'http://localhost:1111/status/'}

EXPECTED_GAUGES = [
    'kong.total_requests',
    'kong.connections_active',
    'kong.connections_waiting',
    'kong.connections_reading',
    'kong.connections_accepted',
    'kong.connections_writing',
    'kong.connections_handled',
]

DATABASES = ['reachable']
