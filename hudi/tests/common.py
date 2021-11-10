# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here, load_jmx_config

HERE = get_here()
HOST = get_docker_hostname()
JMX_PORT = 9999
DEFAULT_MAX_RETURNED_METRICS = 2000

INSTANCE = [{'host': HOST, 'port': JMX_PORT, 'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS}]
CHECK_CONFIG = load_jmx_config()
CHECK_CONFIG['instances'] = INSTANCE
