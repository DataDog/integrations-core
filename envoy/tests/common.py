import os
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(HERE, 'fixtures')

HOST = get_docker_hostname()
PORT = '8001'
INSTANCES = {
    'main': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
    },
    'whitelist': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'metric_whitelist': [
            r'envoy\.cluster\..*',
        ],
    },
    'blacklist': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'metric_blacklist': [
            r'envoy\.cluster\..*',
        ],
    },
    'whitelist_blacklist': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'metric_whitelist': [
            r'envoy\.cluster\.',
        ],
        'metric_blacklist': [
            r'envoy\.cluster\.out',
        ],
    },
}


class MockResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


@lru_cache(maxsize=None)
def response(kind):
    file_path = os.path.join(FIXTURE_DIR, kind)
    if os.path.isfile(file_path):
        with open(file_path, 'rb') as f:
            return MockResponse(f.read(), 200)
    else:
        raise IOError('File `{}` does not exist.'.format(file_path))
