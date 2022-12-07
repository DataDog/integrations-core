# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here, load_jmx_config

HERE = get_here()
HOST = get_docker_hostname()

INSTANCES = [{'host': 'localhost', 'port': '7002'}]

CHECK_CONFIG = load_jmx_config()
CHECK_CONFIG['instances'] = INSTANCES

CHECK_NAME = "weblogic"
