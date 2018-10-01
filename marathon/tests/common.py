# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.base.utils.common import get_docker_hostname


HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
PORT = 8080
