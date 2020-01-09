# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from base64 import urlsafe_b64decode

import pytest

from datadog_checks.dev._env import TESTING_PLUGIN


@pytest.mark.skipif(os.getenv(TESTING_PLUGIN) != 'true', reason="Plugin is not enabled, skipping plugin test...")
def test_runner(dd_environment_runner, mock_e2e_config, mock_e2e_metadata):
    message = dd_environment_runner

    encoded = message.split(' ')[1]
    decoded = urlsafe_b64decode(encoded.encode('utf-8'))
    data = json.loads(decoded.decode('utf-8'))

    assert 'config' in data
    assert 'metadata' in data

    config = data['config']
    metadata = data['metadata']

    assert config == mock_e2e_config
    assert metadata == mock_e2e_metadata
