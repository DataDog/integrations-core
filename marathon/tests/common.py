# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.utils.common import get_docker_hostname
from datadog_checks.dev import get_here


HERE = get_here()
HOST = get_docker_hostname()
PORT = 8080

INSTANCE_INTEGRATION = {
    'url': 'http://{}:{}'.format(HOST, PORT),
    'tags': ['optional:tag1'],
    'label_tags': ['LABEL_NAME'],
    'enable_deployment_metrics': True,
}

EXPECTED_METRICS = [
    'marathon.apps',
    'marathon.deployments',
    'marathon.queue.size',
]

EXPECTED_TAGS = [
    'optional:tag1'
]
