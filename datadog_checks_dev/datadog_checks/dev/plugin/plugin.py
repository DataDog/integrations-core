# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from base64 import urlsafe_b64encode

import pytest

from .._env import E2E_FIXTURE_NAME, TESTING_PLUGIN

try:
    from datadog_checks.base.stubs import aggregator as __aggregator

    @pytest.fixture
    def aggregator():
        """This fixture returns a mocked Agent aggregator with state cleared."""
        __aggregator.reset()
        return __aggregator

except ImportError:
    __aggregator = None

    @pytest.fixture
    def aggregator():
        raise ImportError('datadog-checks-base is not installed!')


@pytest.fixture(scope='session', autouse=True)
def dd_environment_runner(request):
    testing_plugin = os.getenv(TESTING_PLUGIN) == 'true'

    # Do nothing if no e2e action is triggered and continue with tests
    if not testing_plugin and not any(ev.startswith('DDEV_E2E_') for ev in os.environ):  # no cov
        return

    try:
        config = request.getfixturevalue(E2E_FIXTURE_NAME)
    except Exception as e:
        # pytest doesn't export this exception class so we have to do some introspection
        if e.__class__.__name__ == 'FixtureLookupError':
            # Make it explicit for our command
            pytest.exit('NO E2E FIXTURE AVAILABLE')

        raise

    metadata = {}

    # Environment fixture also returned some metadata
    if isinstance(config, tuple):
        config, possible_metadata = config

        # Support only defining the env_type for ease-of-use
        if isinstance(possible_metadata, str):
            metadata['env_type'] = possible_metadata
        else:
            metadata.update(possible_metadata)

    # Default to Docker as that is the most common
    metadata.setdefault('env_type', 'docker')

    data = {
        'config': config,
        'metadata': metadata,
    }

    # Serialize to json
    data = json.dumps(data, separators=(',', ':'))

    # Using base64 ensures:
    # 1. Printing to stdout won't fail
    # 2. Easy parsing since there are no spaces
    message = urlsafe_b64encode(data.encode('utf-8'))

    message = 'DDEV_E2E_START_MESSAGE {} DDEV_E2E_END_MESSAGE'.format(message.decode('utf-8'))

    if testing_plugin:
        return message
    else:  # no cov
        # Exit testing and pass data back up to command
        pytest.exit(message)
