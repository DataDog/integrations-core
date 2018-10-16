# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
import time

import pytest
import requests
from datadog_checks.elastic import ESCheck

from .common import HERE, URL, USER, PASSWORD


CUSTOM_TAGS = ["foo:bar", "baz"]
COMPOSE_FILES_MAP = {
    'elasticsearch_0_90': 'elasticsearch_0_90.yaml',
    '1-alpine': 'legacy.yaml',
    '2-alpine': 'legacy.yaml',
}


@pytest.fixture(scope="session")
def elastic_cluster():
    image_name = os.environ.get("ELASTIC_IMAGE")
    compose_file = COMPOSE_FILES_MAP.get(image_name, 'docker-compose.yaml')
    args = [
        'docker-compose', '-f', os.path.join(HERE, 'compose', compose_file)
    ]
    subprocess.check_call(args + ["up", "-d"])
    print("Waiting for ES to boot...")

    for _ in xrange(20):
        try:
            res = requests.get(URL)
            res.raise_for_status()
            break
        except Exception:
            time.sleep(2)

    # Create an index in ES
    requests.put(URL, '/datadog/')
    yield
    subprocess.check_call(args + ["down"])


@pytest.fixture
def elastic_check():
    return ESCheck('elastic', {}, {})


@pytest.fixture
def instance():
    return {
        'url': URL,
        'username': USER,
        'password': PASSWORD,
        'tags': CUSTOM_TAGS,
    }


@pytest.fixture
def cluster_tags():
    return [
        'url:{}'.format(URL),
        'cluster_name:test-cluster',
    ] + CUSTOM_TAGS


@pytest.fixture
def node_tags():
    return cluster_tags().append('node_name:test-node')
