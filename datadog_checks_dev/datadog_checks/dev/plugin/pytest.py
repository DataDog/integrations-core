# (C) Datadog, Inc. 2018-2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import json
import os
from base64 import urlsafe_b64encode

import pytest

from .._env import (
    AGENT_COLLECTOR_SEPARATOR,
    E2E_FIXTURE_NAME,
    E2E_PARENT_PYTHON,
    TESTING_PLUGIN,
    e2e_active,
    e2e_testing,
    format_config,
    get_env_vars,
    get_state,
    replay_check_run,
    save_state,
    serialize_data,
)

__aggregator = None
__datadog_agent = None


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


@pytest.fixture
def datadog_agent():
    global __datadog_agent

    if __datadog_agent is None:
        try:
            from datadog_checks.base.stubs import datadog_agent as __datadog_agent
        except ImportError:
            raise ImportError('datadog-checks-base is not installed!')

    __datadog_agent.reset()
    return __datadog_agent


@pytest.fixture(scope='session', autouse=True)
def dd_environment_runner(request):
    testing_plugin = os.getenv(TESTING_PLUGIN) == 'true'

    # Do nothing if no e2e action is triggered and continue with tests
    if not testing_plugin and not e2e_active():  # no cov
        return
    # If e2e tests are being run it means the environment has
    # already been spun up so we prevent another invocation
    elif e2e_testing():  # no cov
        # Since the scope is `session` there should only ever be one definition
        fixture_def = request._fixturemanager._arg2fixturedefs[E2E_FIXTURE_NAME][0]

        # Make the underlying function a no-op
        fixture_def.func = lambda: None
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

    # Inject any log configuration
    logs_config = get_state('logs_config', [])
    if logs_config:
        config = format_config(config)
        config['logs'] = logs_config

    # Mount any volumes for Docker
    if metadata['env_type'] == 'docker':
        docker_volumes = get_state('docker_volumes', [])
        if docker_volumes:
            metadata.setdefault('docker_volumes', []).extend(docker_volumes)

    data = {'config': config, 'metadata': metadata}

    message = serialize_data(data)

    message = 'DDEV_E2E_START_MESSAGE {} DDEV_E2E_END_MESSAGE'.format(message)

    if testing_plugin:
        return message
    else:  # no cov
        # Exit testing and pass data back up to command
        pytest.exit(message)


@pytest.fixture
def dd_agent_check(request, aggregator):
    if not e2e_testing():
        pytest.skip('Not running E2E tests')

    # Lazily import to reduce plugin load times for everyone
    from datadog_checks.dev import TempDir, run_command

    def run_check(config=None, **kwargs):
        root = os.path.dirname(request.module.__file__)
        while True:
            if os.path.isfile(os.path.join(root, 'setup.py')):
                check = os.path.basename(root)
                break

            new_root = os.path.dirname(root)
            if new_root == root:
                raise OSError('No Datadog Agent check found')

            root = new_root

        python_path = os.environ[E2E_PARENT_PYTHON]
        env = os.environ['TOX_ENV_NAME']

        check_command = [python_path, '-m', 'datadog_checks.dev', 'env', 'check', check, env, '--json']

        if config:
            config = format_config(config)
            config_file = os.path.join(temp_dir, '{}-{}-{}.json'.format(check, env, urlsafe_b64encode(os.urandom(6))))

            with open(config_file, 'wb') as f:
                output = json.dumps(config).encode('utf-8')
                f.write(output)
            check_command.extend(['--config', config_file])

        for key, value in kwargs.items():
            if value is not False:
                check_command.append('--{}'.format(key.replace('_', '-')))

                if value is not True:
                    check_command.append(str(value))

        result = run_command(check_command, capture=True)
        if AGENT_COLLECTOR_SEPARATOR not in result.stdout:
            raise ValueError(
                '{}{}\nCould not find `{}` in the output'.format(
                    result.stdout, result.stderr, AGENT_COLLECTOR_SEPARATOR
                )
            )

        _, _, collector_output = result.stdout.partition(AGENT_COLLECTOR_SEPARATOR)
        collector_output = collector_output.strip()
        if not collector_output.endswith(']'):
            # JMX needs some additional cleanup
            collector_output = collector_output[: collector_output.rfind(']') + 1]
        collector = json.loads(collector_output)

        replay_check_run(collector, aggregator)

        return aggregator

    # Give an explicit name so we don't shadow other uses
    with TempDir('dd_agent_check') as temp_dir:
        yield run_check


@pytest.fixture
def dd_run_check():
    def run_check(check, extract_message=False):
        error = check.run()

        if error:
            error = json.loads(error)[0]
            if extract_message:
                raise Exception(error['message'])
            else:
                exc_lines = ['']
                exc_lines.extend(error['traceback'].splitlines())
                raise Exception('\n'.join(exc_lines))

        return ''

    return run_check


@pytest.fixture
def dd_get_state():
    return get_state


@pytest.fixture
def dd_save_state():
    return save_state


def pytest_configure(config):
    # pytest will emit warnings if these aren't registered ahead of time
    config.addinivalue_line('markers', 'unit: marker for unit tests')
    config.addinivalue_line('markers', 'integration: marker for integration tests')
    config.addinivalue_line('markers', 'e2e: marker for end-to-end Datadog Agent tests')
