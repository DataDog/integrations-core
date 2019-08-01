# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(HERE, 'compose')
ROOT = os.path.dirname(os.path.dirname(HERE))

CHECK_NAME = 'gunicorn'

HOST = get_docker_hostname()
PORT = 18000

PROC_NAME = 'dd-test-gunicorn'

INSTANCE = {'proc_name': PROC_NAME}
