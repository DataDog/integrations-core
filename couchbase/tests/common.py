# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

HOST = get_docker_hostname()
PORT = '8091'
DATA_PORT = '11210'

URL = 'http://{0}:{1}'.format(HOST, PORT)

USER = 'Administrator'
PASSWORD = 'password'

TAGS = ['optional:tag1']
CHECK_TAGS = TAGS + ['instance:http://{0}:{1}'.format(HOST, PORT)]

BUCKET_NAME = 'cb_bucket'
