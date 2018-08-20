# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from datadog_checks.utils.common import get_docker_hostname

CHECK_NAME = "squid"
HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
