# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTS_HELPER_DIR = os.path.join(ROOT, 'datadog-checks-tests-helper')

CHECK_NAME = 'mysql'

HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')
PORT = 13306
SLAVE_PORT = 13307

USER = 'dog'
PASS = 'dog'
