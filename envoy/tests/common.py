import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')
DOCKER_DIR = os.path.join(HERE, 'docker')
FLAVOR = os.getenv('FLAVOR', 'api_v3')

HOST = get_docker_hostname()
PORT = '8001'
INSTANCES = {
    'main': {'stats_url': 'http://{}:{}/stats'.format(HOST, PORT)},
    'included_metrics': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'metric_whitelist': [r'envoy\.cluster\..*'],
    },
    'excluded_metrics': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'metric_blacklist': [r'envoy\.cluster\..*'],
    },
    'included_excluded_metrics': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'included_metrics': [r'envoy\.cluster\.'],
        'excluded_metrics': [r'envoy\.cluster\.out\.'],
    },
    'collect_server_info': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'collect_server_info': 'false',
    },
}
ENVOY_VERSION = os.getenv('ENVOY_VERSION')
