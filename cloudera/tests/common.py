import os

from datadog_checks.dev import get_docker_hostname, get_here

HOST = get_docker_hostname()
PORT = 7180

INSTANCE = {
    'workload_username': '~',
    'workload_password': '~',
    'api_url': 'http://localhost:8080/api/v48/',
}

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
