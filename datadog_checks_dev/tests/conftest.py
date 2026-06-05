# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from hypothesis import settings

if os.environ.get('REPLAY_PBT_HYPOTHESIS_DEBUG') == 'true':
    settings.register_profile('replay-pbt-ci', print_blob=True)
    settings.load_profile('replay-pbt-ci')


@pytest.fixture(scope='session')
def mock_e2e_config():
    return {'prometheus_url': 'http://localhost:2379/metrics', 'tags': ['tag1:value1', 'tag2:value2']}


@pytest.fixture(scope='session')
def mock_e2e_metadata():
    return {'agent_type': 'vagrant', 'e2e_env_vars': {}, 'future': 'now', 'env_vars': {}}


@pytest.fixture(scope='session')
def dd_environment(mock_e2e_config, mock_e2e_metadata):
    yield mock_e2e_config, mock_e2e_metadata
