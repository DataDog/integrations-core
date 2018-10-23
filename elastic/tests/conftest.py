# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.elastic import ESCheck
from .common import HERE, URL, USER, PASSWORD


CUSTOM_TAGS = ['foo:bar', 'baz']
COMPOSE_FILES_MAP = {
    'elasticsearch_0_90': 'elasticsearch_0_90.yaml',
    '1-alpine': 'legacy.yaml',
    '2-alpine': 'legacy.yaml',
}


def ping_elastic():
    """
    The PUT request we use to ping the server will create an index named `testindex`
    as soon as ES is available. This is just one possible ping strategy but it's needed
    as a fixture for tests that require that index to exist in order to pass.
    """
    response = requests.put('{}/testindex'.format(URL), auth=(USER, PASSWORD))
    response.raise_for_status()


@pytest.fixture(scope='session')
def dd_environment(instance):
    image_name = os.environ.get('ELASTIC_IMAGE')
    compose_file = COMPOSE_FILES_MAP.get(image_name, 'docker-compose.yaml')
    compose_file = os.path.join(HERE, 'compose', compose_file)

    with docker_run(
        compose_file=compose_file,
        conditions=[WaitFor(ping_elastic)],
    ):
        yield instance


@pytest.fixture
def elastic_check():
    return ESCheck('elastic', {}, {})


@pytest.fixture(scope='session')
def instance():
    return {
        'url': URL,
        'username': USER,
        'password': PASSWORD,
        'tags': CUSTOM_TAGS,
    }


@pytest.fixture(scope='session')
def instance_normalize_hostname():
    return {
        'url': URL,
        'username': USER,
        'password': PASSWORD,
        'tags': CUSTOM_TAGS,
        'node_name_as_host': True,
    }


def _cluster_tags():
    tags = [
        'url:{}'.format(URL),
        'cluster_name:test-cluster',
    ]
    tags.extend(CUSTOM_TAGS)

    return tags


@pytest.fixture
def cluster_tags():
    return _cluster_tags()


@pytest.fixture
def node_tags():
    tags = _cluster_tags()
    tags.append('node_name:test-node')
    return tags
