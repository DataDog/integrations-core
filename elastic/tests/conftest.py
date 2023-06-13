# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

import mock
import pytest
import requests
from packaging import version

from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.elastic import ESCheck

from .common import CLUSTER_TAG, ELASTIC_CLUSTER_TAG, ELASTIC_FLAVOR, ELASTIC_VERSION, HERE, PASSWORD, URL, USER

CUSTOM_TAGS = ['foo:bar', 'baz']

INSTANCE = {
    'url': URL,
    'username': USER,
    'password': PASSWORD,
    'tags': CUSTOM_TAGS,
    'tls_verify': False,
    'custom_queries': [
        {
            'endpoint': '/_search',
            'data_path': 'hits.total',
            'columns': [
                {'value_path': 'value', 'name': 'elasticsearch.custom.metric', 'type': 'gauge'},
                {'value_path': 'relation', 'name': 'dynamic_tag', 'type': 'tag'},
            ],
        },
    ],
}


BENCHMARK_INSTANCE = {
    'url': URL,
    'username': USER,
    'password': PASSWORD,
    'tags': CUSTOM_TAGS,
    'tls_verify': False,
}


def ping_elastic():
    """
    The PUT request we use to ping the server will create an index named `testindex`
    as soon as ES is available. This is just one possible ping strategy but it's needed
    as a fixture for tests that require that index to exist in order to pass.
    """
    response = requests.put('{}/testindex'.format(URL), auth=(USER, PASSWORD), verify=False)
    response.raise_for_status()


def create_slm():
    if version.parse(ELASTIC_VERSION) < version.parse('7.4.0'):
        return

    create_backup_body = {"type": "fs", "settings": {"location": "data"}}
    response = requests.put(
        '{}/_snapshot/my_repository?pretty'.format(INSTANCE['url']),
        json=create_backup_body,
        auth=(INSTANCE['username'], INSTANCE['password']),
        verify=False,
    )
    response.raise_for_status()

    create_slm_body = {
        "schedule": "0 30 1 * * ?",
        "name": "<daily-snap-{now/d}>",
        "repository": "my_repository",
        "config": {"indices": ["data-*", "important"], "ignore_unavailable": False, "include_global_state": False},
        "retention": {"expire_after": "30d", "min_count": 5, "max_count": 50},
    }
    response = requests.put(
        '{}/_slm/policy/daily-snapshots?pretty'.format(INSTANCE['url']),
        json=create_slm_body,
        auth=(INSTANCE['username'], INSTANCE['password']),
        verify=False,
    )
    response.raise_for_status()


def index_starts_with_dot():
    create_dot_testindex = requests.put('{}/.testindex'.format(URL), auth=(USER, PASSWORD), verify=False)
    create_dot_testindex.raise_for_status()


@pytest.fixture(scope='session')
def dd_environment():
    # opensearch doesn't play well with xpack env vars
    compose_file = '{}-docker-compose.yaml'.format(ELASTIC_FLAVOR)
    compose_file = os.path.join(HERE, 'compose', compose_file)

    with docker_run(
        compose_file=compose_file,
        conditions=[
            WaitFor(ping_elastic, attempts=100),
            WaitFor(index_starts_with_dot, attempts=100),
            WaitFor(create_slm, attempts=5),
        ],
        attempts=2,
        attempts_wait=10,
    ):
        yield INSTANCE


@pytest.fixture
def elastic_check():
    return ESCheck('elastic', {}, instances=[INSTANCE])


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def benchmark_elastic_check():
    return ESCheck('elastic', {}, instances=[BENCHMARK_INSTANCE])


@pytest.fixture
def benchmark_instance():
    return copy.deepcopy(BENCHMARK_INSTANCE)


@pytest.fixture
def instance_normalize_hostname():
    return {
        'url': URL,
        'username': USER,
        'password': PASSWORD,
        'tags': CUSTOM_TAGS,
        'node_name_as_host': True,
        'tls_verify': False,
    }


@pytest.fixture
def version_metadata():
    if '-' in ELASTIC_VERSION:
        base, release = ELASTIC_VERSION.split('-')
        parts = base.split('.')
    else:
        release = None
        parts = ELASTIC_VERSION.split('.')

    major = parts[0]
    minor = parts[1] if len(parts) > 1 else mock.ANY
    patch = parts[2] if len(parts) > 2 else mock.ANY
    return exclude_undefined_keys(
        {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': mock.ANY,
            'version.release': release,
        }
    )


def _cluster_tags():
    tags = ['url:{}'.format(URL)] + ELASTIC_CLUSTER_TAG + CLUSTER_TAG
    tags.extend(CUSTOM_TAGS)

    return tags


@pytest.fixture
def new_cluster_tags():
    tags = ['url:{}'.format(URL)] + ELASTIC_CLUSTER_TAG
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


@pytest.fixture
def slm_tags():
    tags = _cluster_tags()
    tags.append('policy:daily-snapshots')
    tags.append('repository:my_repository')
    return tags
