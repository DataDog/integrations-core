# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()
USE_FLY_LAB = os.environ.get("USE_FLY_LAB")
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
FLY_ACCESS_TOKEN = os.environ.get('FLY_ACCESS_TOKEN')
ORG_SLUG = os.environ.get('FLY_ORG_SLUG')

INSTANCE = {
    'org_slug': 'test',
    'empty_default_hostname': True,
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'machines_api_endpoint': 'http://localhost:4280',
    'headers': {'Authorization': 'Bearer Test'},
}

LAB_INSTANCE = {
    'org_slug': ORG_SLUG,
    'headers': {'Authorization': f'Bearer {FLY_ACCESS_TOKEN}'},
    'machines_api_endpoint': 'https://api.machines.dev',
    'empty_default_hostname': True,
}
