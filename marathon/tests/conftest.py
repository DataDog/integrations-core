# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import json

import pytest

from datadog_checks.marathon import Marathon
from .common import HERE, HOST, PORT


def read_fixture_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return json.loads(f.read())


@pytest.fixture
def check():
    return Marathon('marathon', {}, {}, [{}])


@pytest.fixture
def instance():
    return {
        'url': 'http://{}:{}'.format(HOST, PORT),
        'tags': ['optional:tag1'],
        'label_tags': ['LABEL_NAME'],
        'enable_deployment_metrics': True
    }


@pytest.fixture
def apps():
    return read_fixture_file('apps.json')


@pytest.fixture
def deployments():
    return read_fixture_file('deployments.json')


@pytest.fixture
def queue():
    return read_fixture_file('queue.json')


@pytest.fixture
def groups():
    return read_fixture_file('groups.json')
