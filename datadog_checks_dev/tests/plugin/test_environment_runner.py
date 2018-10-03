# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from base64 import urlsafe_b64decode


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
