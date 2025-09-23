# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.nginx import Nginx

from .common import HERE, HOST, PORT, PORT_SSL, TAGS, USING_VTS


@pytest.fixture(scope='session')
def dd_environment(instance, instance_vts):
    if USING_VTS:
        config_dir = os.path.join(HERE, 'nginx_vts')
        instance = instance_vts
    else:
        config_dir = os.path.join(HERE, 'docker', 'nginx')

    with docker_run(
        os.path.join(HERE, 'docker', 'docker-compose.yaml'),
        env_vars={'NGINX_CONFIG_FOLDER': config_dir},
        endpoints='http://{}:{}/nginx_status'.format(HOST, PORT),
    ):
        yield instance


INSTANCE = {
    'nginx_status_url': 'http://{}:{}/nginx_status'.format(HOST, PORT),
    'tags': TAGS,
    'disable_generic_tags': True,
}


@pytest.fixture
def check():
    return lambda instance: Nginx('nginx', {}, [instance])


@pytest.fixture(scope='session')
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture(scope='session')
def instance_plus_v7():
    base_instance = copy.deepcopy(INSTANCE)
    base_instance['nginx_status_url'] = 'http://localhost:8080/api'
    base_instance['use_plus_api'] = True
    base_instance['use_plus_api_stream'] = True
    base_instance['plus_api_version'] = 7
    return base_instance


@pytest.fixture(scope='session')
def instance_plus_v7_no_stream():
    base_instance = copy.deepcopy(INSTANCE)
    base_instance['nginx_status_url'] = 'http://localhost:8080/api'
    base_instance['use_plus_api'] = True
    base_instance['use_plus_api_stream'] = False
    base_instance['plus_api_version'] = 7
    return base_instance


@pytest.fixture
def instance_ssl():
    return {
        'nginx_status_url': 'https://{}:{}/nginx_status'.format(HOST, PORT_SSL),
        'tags': TAGS,
        'disable_generic_tags': True,
    }


@pytest.fixture(scope='session')
def instance_vts():
    return {
        'nginx_status_url': 'http://{}:{}/vts_status'.format(HOST, PORT),
        'tags': TAGS,
        'use_vts': True,
        'disable_generic_tags': True,
    }


@pytest.fixture(scope='session')
def mocked_instance_vts():
    return {
        'tags': TAGS,
        'nginx_status_url': 'http://{}:{}/vts_status'.format(HOST, PORT),
        'use_vts': True,
        'disable_generic_tags': True,
    }
