# C Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License see LICENSE
import os
import pytest

CHECK_NAME = 'openstack'

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

ALL_IDS = ['server-1', 'server-2', 'other-1', 'other-2']
EXCLUDED_NETWORK_IDS = ['server-1', 'other-.*']
EXCLUDED_SERVER_IDS = ['server-2', 'other-.*']
FILTERED_NETWORK_ID = 'server-2'
FILTERED_SERVER_ID = 'server-1'
FILTERED_BY_PROJ_SERVER_ID = ['server-1', 'server-2']

MOCK_CONFIG = {
    'init_config': {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_network_ids': EXCLUDED_NETWORK_IDS,
    },
    'instances': [
        {
            'name': 'test_name', 'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}}
        }
    ]
}


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator
