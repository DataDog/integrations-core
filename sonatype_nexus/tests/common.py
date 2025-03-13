# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(HERE, 'compose')

INSTANCE = {
    "username": "admin",
    "password": "your_password",
    "server_url": "https://0.0.0.0:8081",
    "min_collection_interval": 400,
    "tags": ["sample_tag:sample_value"],
}
