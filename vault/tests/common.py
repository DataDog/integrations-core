from datadog_checks.utils.common import get_docker_hostname

HOST = get_docker_hostname()
PORT = '8200'
INSTANCES = {
    'main': {
        'api_url': 'http://{}:{}/v1'.format(HOST, PORT),
        'detect_leader': True,
    },
    'bad_url': {
        'api_url': 'http://1.2.3.4:555/v1',
        'timeout': 1,
    },
    'no_leader': {
        'api_url': 'http://{}:{}/v1'.format(HOST, PORT),
    },
    'invalid': {},
}


class MockResponse:
    def __init__(self, j):
        self.j = j
        self.status_code = 200

    def json(self):
        return self.j
