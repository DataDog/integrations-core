# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

HOST = os.getenv('DOCKER_HOSTNAME', '127.0.0.1')
PORT = 8082
HERE = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "host": HOST,
    "port": PORT,
    "api_key": "pdns_api_key"
}

CONFIG_V4 = {
    "host": HOST,
    "port": PORT,
    "version": 4,
    "api_key": "pdns_api_key"
}
