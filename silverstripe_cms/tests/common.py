# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(HERE, 'compose')

INSTANCE = {
    "SILVERSTRIPE_DATABASE_TYPE": "MySQL",
    "SILVERSTRIPE_DATABASE_NAME": "silverstripe_db",
    "SILVERSTRIPE_DATABASE_SERVER_IP": "127.0.0.1",
    "SILVERSTRIPE_DATABASE_PORT": 3306,
    "SILVERSTRIPE_DATABASE_USERNAME": "silverstripe_user",
    "SILVERSTRIPE_DATABASE_PASSWORD": "your_password",
    "min_collection_interval": 300,
    "tags": ["sample_tag:sample_value"],
}
