# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import shutil

import pytest
import requests
import yaml

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.dev.docker import get_container_ip

from .common import (
    AUTODISCOVERY_TYPE,
    COMPOSE_DIR,
    PORT,
    SCALAR_OBJECTS,
    SCALAR_OBJECTS_WITH_TAGS,
    SNMP_CONTAINER_NAME,
    TABULAR_OBJECTS,
    generate_container_instance_config,
)

FILES = [
    "https://ddintegrations.blob.core.windows.net/snmp/3850.snmprec",
]

E2E_METADATA = {
    'start_commands': [
        # Ensure the Agent has access to profile definition files and auto_conf.
        'cp -r /home/snmp/datadog_checks/snmp/data/profiles /etc/datadog-agent/conf.d/snmp.d/',
        'cp -r /home/snmp/datadog_checks/snmp/data/auto_conf.yaml /etc/datadog-agent/conf.d/snmp.d/auto_conf.yaml',
    ],
}


@pytest.fixture(scope='session')
def dd_environment():
    e2e_metadata = E2E_METADATA
    with TempDir('snmp') as tmp_dir:
        data_dir = os.path.join(tmp_dir, 'data')
        env = {'DATA_DIR': data_dir}
        if not os.path.exists(data_dir):
            shutil.copytree(os.path.join(COMPOSE_DIR, 'data'), data_dir)
            for data_file in FILES:
                response = requests.get(data_file)
                with open(os.path.join(data_dir, data_file.rsplit('/', 1)[1]), 'wb') as output:
                    output.write(response.content)

        with docker_run(os.path.join(COMPOSE_DIR, 'docker-compose.yaml'), env_vars=env, log_patterns="Listening at"):
            if AUTODISCOVERY_TYPE == 'agent':
                instance_config = {}
                e2e_metadata['docker_volumes'] = [
                    '{}:/etc/datadog-agent/datadog.yaml'.format(create_datadog_conf_file(tmp_dir))
                ]
            else:
                instance_config = generate_container_instance_config(
                    SCALAR_OBJECTS + SCALAR_OBJECTS_WITH_TAGS + TABULAR_OBJECTS
                )
            yield instance_config, E2E_METADATA


def create_datadog_conf_file(tmp_dir):
    datadog_conf = {
        'snmp_listener': {
            'workers': 4,
            'discovery_interval': 10,
            'configs': [
                {
                    'network': '{}/28'.format(get_container_ip(SNMP_CONTAINER_NAME)),
                    'port': PORT,
                    'community': 'network',
                    'version': 2,
                    'timeout': 1,
                    'retries': 2,
                }
            ],
        },
        'listeners': [{'name': 'snmp'}],
    }
    datadog_conf_file = os.path.join(tmp_dir, 'datadog.yaml')
    with open(datadog_conf_file, 'w') as file:
        file.write(yaml.dump(datadog_conf))
    return datadog_conf_file


@pytest.fixture
def container_ip():
    return get_container_ip(SNMP_CONTAINER_NAME)
