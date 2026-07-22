# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(HERE, "fixtures")

INSTANCE = {
    "region": "mypurecloud.com",
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
    "mos_threshold": 4.2,
    "min_collection_interval": 300,
    "tags": ["team:voice"],
}


def read_fixture(name):
    """Return the raw JSON text of a Genesys API response fixture."""
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()
