# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

PORT = '8500'

HOST = get_docker_hostname()

URL = 'http://{}:{}'.format(HOST, PORT)

CHECK_NAME = 'consul'

HERE = os.path.dirname(os.path.abspath(__file__))
