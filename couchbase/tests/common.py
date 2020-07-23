# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

# Networking
HOST = get_docker_hostname()
PORT = '8091'
QUERY_PORT = '8093'

# Tags and common bucket name
CUSTOM_TAGS = ['optional:tag1']
CHECK_TAGS = CUSTOM_TAGS + ['instance:http://{}:{}'.format(HOST, PORT)]
BUCKET_NAME = 'cb_bucket'

URL = 'http://{}:{}'.format(HOST, PORT)
QUERY_URL = 'http://{}:{}'.format(HOST, QUERY_PORT)
CB_CONTAINER_NAME = 'couchbase-standalone'
USER = 'Administrator'
PASSWORD = 'password'

DEFAULT_INSTANCE = {'server': URL, 'user': USER, 'password': PASSWORD, 'timeout': 0.5, 'tags': CUSTOM_TAGS}
