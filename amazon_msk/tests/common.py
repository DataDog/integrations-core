# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.utils import read_file

HERE = get_here()
HOST = get_docker_hostname()
JMX_PORT = 11001
NODE_PORT = 11002
INSTANCE_LEGACY = {
    'cluster_arn': 'arn:aws:kafka:us-east-1:1234567890:cluster/msk-integrate/9dabe192-8f48-4421-8b94-191780c69e1c',
    'tags': ['test:msk'],
}
INSTANCE = dict(use_openmetrics=True, **INSTANCE_LEGACY)
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

E2E_METADATA = {
    'post_install_commands': ['pip install /home/mock_boto3'],
    'docker_volumes': ['{}:/home/mock_boto3'.format(os.path.join(HERE, 'mock_boto3'))],
}


def get_metrics_fixture_path(exporter_type):
    return os.path.join(HERE, 'docker', 'exporter_{}'.format(exporter_type), 'metrics')


def read_api_fixture():
    return read_file(os.path.join(HERE, 'fixtures', 'list_nodes.json'))


def read_e2e_api_fixture():
    return read_file(os.path.join(HERE, 'mock_boto3', 'boto3', 'list_nodes.json'))
