# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'

CREDENTIALS = [{'username': 'dummy-user', 'password': 'dummy-password'}]

STATIC_INSTANCE = {
    'firewalls': ['192.0.2.10'],
    'firewall_credentials': CREDENTIALS,
}

PANORAMA_INSTANCE = {
    'panorama_host': 'panorama.example.com',
    'panorama_api_key': 'dummy-api-key',
    'firewall_credentials': CREDENTIALS,
}

INSTANCE = STATIC_INSTANCE
