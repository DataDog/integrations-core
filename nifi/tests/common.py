# ABOUTME: Shared constants and instance configurations for NiFi tests.
# ABOUTME: Provides Docker hostname, ports, credentials, and test instance configs.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 8443
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

NIFI_USERNAME = 'admin'
NIFI_PASSWORD = 'ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB'
NIFI_API_URL = f'https://{HOST}:{PORT}/nifi-api'

INSTANCE = {
    'api_url': NIFI_API_URL,
    'username': NIFI_USERNAME,
    'password': NIFI_PASSWORD,
    'tls_verify': False,
}

CHECK_CONFIG = {
    'init_config': {},
    'instances': [INSTANCE],
}
