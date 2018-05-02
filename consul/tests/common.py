# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.utils.common import get_docker_hostname

PORT = '8500'

HOST = get_docker_hostname()

URL = "http://{0}:{1}".format(HOST, PORT)

CHECK_NAME = 'consul'

HERE = os.path.dirname(os.path.abspath(__file__))
