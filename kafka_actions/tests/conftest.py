# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64

import pytest


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {
        'remote_config_id': 'test-config-id',
        'kafka_connect_str': 'localhost:9092',
        'produce_message': {
            'cluster': 'test-cluster',
            'topic': 'test-topic',
            'key': base64.b64encode(b'test-key').decode('utf-8'),
            'value': base64.b64encode(b'test-value').decode('utf-8'),
        },
    }
