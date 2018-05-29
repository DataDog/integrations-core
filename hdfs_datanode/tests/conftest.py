# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import os
import json
from mock import patch

# 3rd party
import pytest

from .common import HERE


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope='session', autouse=True)
def mocked_request():
    patcher = patch('requests.get', new=requests_get_mock)
    patcher.start()
    yield
    patcher.stop()


def requests_get_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    datanode_beans_file_path = os.path.join(HERE, 'fixtures', 'hdfs_datanode_jmx')
    with open(datanode_beans_file_path, 'r') as f:
        body = f.read()
        return MockResponse(body, 200)
