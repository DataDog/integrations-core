# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here

URL = 'http://{}:80'.format(get_docker_hostname())
INSTANCE = {
    'url': URL,
    'username': 'admin',
    'password': 'Harbor12345',
    'tls_ca_cert': '/Users/florian.veaux/Downloads/harbor1.8/data/certs/ca.crt',
}


@pytest.fixture(scope='session')
def dd_environment(instance):
    yield instance


@pytest.fixture
def instance():
    return INSTANCE.copy()
