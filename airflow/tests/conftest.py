# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from os import path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import URL

HERE = os.path.dirname(os.path.abspath(__file__))

TMP_DATA_FOLDER = path.join(HERE, 'compose', 'tmp_data')

E2E_METADATA = {
    'docker_volumes': ['{}/datadog.yaml:/etc/datadog-agent/datadog.yaml'.format(TMP_DATA_FOLDER)],
}


def get_readme_mappings():
    with open(path.join(HERE, '..', 'README.md'), 'r') as f:
        readme = f.read()

    start = readme.find('dogstatsd_mapper_profiles:')
    end = readme[start:].find('```')
    return readme[start : start + end]


def create_datadog_config(datadog_config):
    with open(path.join(TMP_DATA_FOLDER, 'datadog.yaml'), 'w') as f:
        f.write(datadog_config)


@pytest.fixture(scope='session')
def dd_environment(instance):
    datadog_config = """
dogstatsd_metrics_stats_enable: true
"""
    create_datadog_config(datadog_config + get_readme_mappings())
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[CheckEndpoints(URL + '/api/experimental/test', attempts=100)],
    ):
        yield instance, E2E_METADATA


@pytest.fixture(scope='session')
def instance():
    return {'url': URL}
