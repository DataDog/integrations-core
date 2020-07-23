# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = 'hive'

HERE = get_here()
HOST = get_docker_hostname()

METASTORE_PORT = 8808
SERVER_PORT = 8809
