# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.utils.common import get_docker_hostname

HERE = get_here()
HOST = get_docker_hostname()
PORT = '5050'

INSTANCE = {'url': 'http://{}:{}'.format(HOST, PORT), 'tags': ['instance:mytag1']}

CHECK_NAME = "mesos_master"
FIXTURE_DIR = os.path.join(HERE, 'fixtures')
