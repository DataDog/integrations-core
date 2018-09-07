# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

HOST = get_docker_hostname()
PORT = 24220
BAD_PORT = 24222

URL = "http://{}:{}/api/plugins.json".format(HOST, PORT)
BAD_URL = "http://{}:{}/api/plugins.json".format(HOST, BAD_PORT)

CHECK_NAME = 'fluentd'
