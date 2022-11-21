import os

from datadog_checks.dev import get_here

INSTANCE = {
    'workload_username': '~',
    'workload_password': 'wyz*xbw7cej*mbh9VUW',
    'api_url': '~',
}

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')