# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os.path
from datadog_checks.utils.common import get_docker_hostname

HOST = get_docker_hostname()
PORT = '1978'

URL = 'http://{0}:{1}'.format(HOST, PORT)

HERE = os.path.dirname(os.path.abspath(__file__))
