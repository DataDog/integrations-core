# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

# Networking
HOST = get_docker_hostname()
PORT = '8091'
SYSTEM_VITALS_PORT = '8093'
URL = 'http://{}:{}'.format(HOST, PORT)
SYSTEM_VITALS_URL = 'http://{}:{}'.format(HOST, SYSTEM_VITALS_PORT)

CB_CONTAINER_NAME = 'couchbase-standalone'

# Authentication
USER = 'Administrator'
PASSWORD = 'password'

# Tags and common bucket name
CUSTOM_TAGS = ['optional:tag1']
CHECK_TAGS = CUSTOM_TAGS + ['instance:http://{}:{}'.format(HOST, PORT)]
BUCKET_NAME = 'cb_bucket'

CONFIG = {
    'instances': [{
        'server': URL,
        'user': USER,
        'password': PASSWORD,
        'timeout': 0.5,
        'tags': list(CUSTOM_TAGS),
    }]
}

CONFIG_QUERY = {
    'instances': [{
        'server': URL,
        'user': USER,
        'password': PASSWORD,
        'timeout': 0.5,
        'tags': list(CUSTOM_TAGS),
        'query_monitoring_url': SYSTEM_VITALS_URL,
    }]
}
