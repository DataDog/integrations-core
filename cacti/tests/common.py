# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.cacti import CactiCheck

HERE = get_here()
HOST = get_docker_hostname()

# ID
CONTAINER_NAME = "dd-test-cacti"

RRD_PATH = '/var/lib/cacti/rra'

INSTANCE_INTEGRATION = {'resourcemanager_uri': HOST, 'collect_task_metrics': True}

EXPECTED_METRICS = {
}