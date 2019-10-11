# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import mock

from datadog_checks.dev import docker_run
from datadog_checks.nginx import Nginx

from .common import HERE, HOST, PORT, PORT_SSL, TAGS, USING_VTS, NGINX_VERSION


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


@pytest.fixture
def check():
    return lambda instance: Nginx('nginx', {}, [instance])


@pytest.fixture(scope='session')
def instance():
    return {'nginx_status_url': 'http://{}:{}/nginx_status'.format(HOST, PORT), 'tags': TAGS}


@pytest.fixture
def instance_ssl():
    return {'nginx_status_url': 'https://{}:{}/nginx_status'.format(HOST, PORT_SSL), 'tags': TAGS}


@pytest.fixture(scope='session')
def instance_vts():
    return {'nginx_status_url': 'http://{}:{}/vts_status'.format(HOST, PORT), 'tags': TAGS, 'use_vts': True}


@pytest.fixture(scope='session')
def version_metadata():
    # vts currently defaults to using version 1.13
    version = '1.13' if USING_VTS else version = NGINX_VERSION.split(':')[1]
    
    major, minor = version.split('.')

    return {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': mock.ANY,
        'version.raw': mock.ANY,
    }