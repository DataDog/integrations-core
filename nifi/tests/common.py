# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# ABOUTME: Shared constants and instance configurations for NiFi tests.
# ABOUTME: Provides Docker hostname, ports, credentials, and test instance configs.
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

E2E_INSTANCE = {
    **INSTANCE,
    'collect_connection_metrics': True,
    'collect_processor_metrics': True,
}

E2E_CHECK_CONFIG = {
    'init_config': {},
    'instances': [E2E_INSTANCE],
}
