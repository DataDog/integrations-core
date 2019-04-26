# (C) Datadog, Inc. 2018-2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import json
import os
from base64 import urlsafe_b64encode

import pytest

from .._env import E2E_FIXTURE_NAME, TESTING_PLUGIN, e2e_active, get_env_vars

__aggregator = None


@pytest.fixture
def aggregator():
    """This fixture returns a mocked Agent aggregator with state cleared."""
    global __aggregator

    # Since this plugin is loaded before pytest-cov, we need to import lazily so coverage
    # can see imports, class/function definitions, etc. of the base package.
    if __aggregator is None:
        try:
            from datadog_checks.base.stubs import aggregator as __aggregator
        except ImportError:
            raise ImportError('datadog-checks-base is not installed!')

    __aggregator.reset()
    return __aggregator


@pytest.fixture(scope='session', autouse=True)
def dd_environment_runner(request):
    testing_plugin = os.getenv(TESTING_PLUGIN) == 'true'

    # Do nothing if no e2e action is triggered and continue with tests
    if not testing_plugin and not e2e_active():  # no cov
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

    # Save any environment variables
    metadata.setdefault('env_vars', {})
    metadata['env_vars'].update(get_env_vars(raw=True))

    data = {'config': config, 'metadata': metadata}

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
