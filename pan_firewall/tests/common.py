# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'

INSTANCE = {
    'firewalls': [{'host': 'fw-a.example.com', 'username': 'dummy-user', 'password': 'dummy-password'}],
}
