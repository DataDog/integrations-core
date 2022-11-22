import os

from datadog_checks.dev import get_here

INSTANCE = {
    'workload_username': '~',
    'workload_password': '~',
    'api_url': '~',
}

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
