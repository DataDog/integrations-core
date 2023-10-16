# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import json
import os
import re
import warnings
from base64 import urlsafe_b64encode
from collections import namedtuple  # Not using dataclasses for Py2 compatibility
from io import open
from typing import Dict, List, Optional, Tuple  # noqa: F401

import pytest
from six import PY2, ensure_text

from .._env import (
    E2E_FIXTURE_NAME,
    E2E_PARENT_PYTHON,
    E2E_RESULT_FILE,
    SKIP_ENVIRONMENT,
    TESTING_PLUGIN,
    e2e_active,
    e2e_testing,
    format_config,
    get_env_vars,
    get_state,
    replay_check_run,
    save_state,
    serialize_data,
    set_up_env,
    tear_down_env,
)

__aggregator = None
__datadog_agent = None
MockResponse = None


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
    # Skip the runner if the skip environment variable is specified
    do_skip = os.getenv(SKIP_ENVIRONMENT) == 'true'

    testing_plugin = os.getenv(TESTING_PLUGIN) == 'true'

    # Do nothing if no e2e action is triggered and continue with tests
    if not testing_plugin and not e2e_active() and not do_skip:  # no cov
        return
    # If e2e tests are being run it means the environment has
    # already been spun up so we prevent another invocation
    elif e2e_testing() or do_skip:  # no cov
        # Since the scope is `session` there should only ever be one definition
        fixture_def = request._fixturemanager._arg2fixturedefs[E2E_FIXTURE_NAME][0]

        # Make the underlying function a no-op
        fixture_def.func = lambda *args, **kwargs: None
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

        # Support only defining the agent_type for ease-of-use
        if isinstance(possible_metadata, str):
            metadata['agent_type'] = possible_metadata
        else:
            metadata.update(possible_metadata)

    # Inject any log configuration
    logs_config = get_state('logs_config', [])
    if logs_config:
        config = format_config(config)
        config['logs'] = logs_config

    agent_type = metadata.get('agent_type')

    # Mount any volumes for Docker
    if agent_type == 'docker':
        docker_volumes = get_state('docker_volumes', [])
        if docker_volumes:
            metadata.setdefault('docker_volumes', []).extend(docker_volumes)

    # Save any environment variables
    metadata['e2e_env_vars'] = get_env_vars(raw=True)

    data = {'config': config, 'metadata': metadata}

    message_template = 'DDEV_E2E_START_MESSAGE {} DDEV_E2E_END_MESSAGE'

    if testing_plugin:
        return message_template.format(serialize_data(data))
    else:  # no cov
        # Exit testing and pass data back up to command
        if E2E_RESULT_FILE in os.environ:
            with open(os.environ[E2E_RESULT_FILE], 'w', encoding='utf-8') as f:
                f.write(ensure_text(json.dumps(data)))

            # Rather than exiting we skip every test to avoid the following output:
            # !!!!!!!!!! _pytest.outcomes.Exit: !!!!!!!!!!
            pytest.skip()
        else:
            pytest.exit(message_template.format(serialize_data(data)))


# Manipulate the output if we are spinning up or down an environment.
#
# Both of these conditions will be true during normal testing while only
# one of them will be true when performing the logic.
if not all([set_up_env(), tear_down_env()]):

    def pytest_report_teststatus(report, config):
        """
        https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_report_teststatus
        """
        # Skipping every test displays an `s` for each even when using
        # the minimum verbosity so we force zero output
        if report.skipped:
            return 'skipped', '', ''


@pytest.fixture
def dd_agent_check(request, aggregator, datadog_agent):
    if not e2e_testing():
        pytest.skip('Not running E2E tests')

    # Lazily import to reduce plugin load times for everyone
    from datadog_checks.dev import TempDir, run_command

    def run_check(config=None, **kwargs):
        root = os.path.dirname(request.module.__file__)
        while True:
            if os.path.isfile(os.path.join(root, 'pyproject.toml')) or os.path.isfile(os.path.join(root, 'setup.py')):
                check = os.path.basename(root)
                break

            new_root = os.path.dirname(root)
            if new_root == root:
                raise OSError('No Datadog Agent check found')

            root = new_root

        python_path = os.environ[E2E_PARENT_PYTHON]
        env = os.environ['HATCH_ENV_ACTIVE']

        check_command = [python_path, '-m', 'ddev', 'env', 'agent', check, env, 'check', '--json']

        if config:
            config = format_config(config)
            config_file = os.path.join(temp_dir, '{}-{}-{}.json'.format(check, env, urlsafe_b64encode(os.urandom(6))))

            with open(config_file, 'wb') as f:
                output = json.dumps(config).encode('utf-8')
                f.write(output)
            check_command.extend(['--config-file', config_file])

        # TODO: remove these legacy flags when all usage of this fixture is migrated
        if 'rate' in kwargs:
            kwargs['check_rate'] = kwargs.pop('rate')

        if 'times' in kwargs:
            kwargs['check_times'] = kwargs.pop('times')

        for key, value in kwargs.items():
            if value is not False:
                check_command.append('--{}'.format(key.replace('_', '-')))

                if value is not True:
                    check_command.append(str(value))

        result = run_command(check_command, capture=True)

        matches = re.findall(r'((?:\{ \[|\[).*?\n(?:\} \]|\]))', result.stdout, re.DOTALL)

        if not matches:
            message_parts = []
            debug_result = run_command(['docker', 'logs', 'dd_{}_{}'.format(check, env)], capture=True)
            if not debug_result.code:
                message_parts.append(debug_result.stdout + debug_result.stderr)

            message_parts.append(result.stdout + result.stderr)
            raise ValueError('{}\nCould not find valid check output'.format('\n'.join(message_parts)))

        for raw_json in matches:
            try:
                collector = json.loads(raw_json)
            except Exception as e:
                raise Exception("Error loading json: {}\nCollector Json Output:\n{}".format(e, raw_json))
            replay_check_run(collector, aggregator, datadog_agent)

        return aggregator

    # Give an explicit name so we don't shadow other uses
    with TempDir('dd_agent_check') as temp_dir:
        yield run_check


@pytest.fixture
def dd_run_check():
    checks = {}

    def run_check(check, extract_message=False, cancel=True):
        if cancel:
            checks[id(check)] = check

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

    yield run_check

    for c in checks.values():
        try:
            c.cancel()
        except Exception:
            pass


@pytest.fixture(scope='session')
def dd_get_state():
    return get_state


@pytest.fixture(scope='session')
def dd_save_state():
    return save_state


@pytest.fixture(scope='session')
def dd_default_hostname():
    import socket

    return socket.gethostname().lower()


@pytest.fixture
def mock_http_response(mocker):
    # Lazily import `requests` as it may be costly under certain conditions
    global MockResponse
    if MockResponse is None:
        from ..http import MockResponse

    yield lambda *args, **kwargs: mocker.patch(
        kwargs.pop('method', 'requests.get'), return_value=MockResponse(*args, **kwargs)
    )


@pytest.fixture
def mock_performance_objects(mocker, dd_default_hostname):
    def mock_perf_objects(
        perf_objects,  # type: Dict[str, Tuple[List[Optional[str]], Dict[str, List[float]]]]
        server=dd_default_hostname,  # type: str
    ):
        import win32pdh

        mocker.patch('win32pdh.OpenQuery')
        mocker.patch('win32pdh.CollectQueryData')
        mocker.patch('win32pdh.AddCounter', side_effect=lambda _, path: path)
        mocker.patch('win32pdh.AddEnglishCounter', side_effect=lambda _, path: path)
        mocker.patch('win32pdh.RemoveCounter')
        mocker.patch('win32pdh.EnumObjects', return_value=list(perf_objects))

        def enum_object_items(data_source, machine_name, object_name, detail_level):
            instances, counter_values = perf_objects[object_name]
            return list(counter_values), instances if instances != [None] else []

        mocker.patch('win32pdh.EnumObjectItems', side_effect=enum_object_items)

        counters = {}
        for object_name, data in perf_objects.items():
            instances, counter_values = data
            instance_counts = {instance_name: 0 for instance_name in instances}
            instance_indices = []
            for instance_name in instances:
                instance_indices.append(instance_counts[instance_name])
                instance_counts[instance_name] += 1

            for counter_name, values in counter_values.items():
                if len(values) == 0:
                    continue

                if instance_name is None:
                    # Single counter
                    counters[win32pdh.MakeCounterPath((server, object_name, None, None, 0, counter_name))] = values[0]
                else:
                    # Multiple instance counter
                    counter_path_wildcard = win32pdh.MakeCounterPath((server, object_name, '*', None, 0, counter_name))
                    instance_values_wildcard = {}
                    for instance_name, index, value in zip(instances, instance_indices, values):
                        # Add single instance counter (in case like IIS is using exact per-instnace wildcard)
                        counter_path_exact = win32pdh.MakeCounterPath(
                            (server, object_name, instance_name, None, 0, counter_name)
                        )
                        instance_values_exact = {}
                        instance_values_exact[instance_name] = value
                        counters[counter_path_exact] = instance_values_exact

                        # Add wildcard path/value
                        if index == 0:
                            instance_values_wildcard[instance_name] = value
                        elif index == 1:
                            # Replace single value as a two instance list
                            non_unique_instance_value = [instance_values_wildcard[instance_name], value]
                            instance_values_wildcard[instance_name] = non_unique_instance_value
                        else:
                            # Append to the list
                            non_unique_instance_value = instance_values_wildcard[instance_name]
                            non_unique_instance_value.append(value)
                            instance_values_wildcard[instance_name] = non_unique_instance_value

                    counters[counter_path_wildcard] = instance_values_wildcard

        validate_path_fn_name = 'datadog_checks.base.checks.windows.perf_counters.counter.validate_path'
        mocker.patch(validate_path_fn_name, side_effect=lambda x, y, path: True if path in counters else False)
        mocker.patch('win32pdh.GetFormattedCounterValue', side_effect=lambda path, _: (None, counters[path]))
        get_counter_values_fn_name = 'datadog_checks.base.checks.windows.perf_counters.counter.get_counter_values'
        mocker.patch(get_counter_values_fn_name, side_effect=lambda path, _: counters[path])

    return mock_perf_objects


TestType = namedtuple('TestType', 'name description filepath_match')
TEST_TYPES = (
    TestType('unit', 'marker for unit tests', 'test_unit'),
    TestType('integration', 'marker for integration tests', 'test_integration'),
    TestType('e2e', 'marker for end-to-end tests', 'test_e2e'),
)


def pytest_configure(config):
    # pytest will emit warnings if these aren't registered ahead of time
    for ttype in TEST_TYPES:
        config.addinivalue_line('markers', '{}: {}'.format(ttype.name, ttype.description))

    config.addinivalue_line("markers", "latest_metrics: marker for verifying support of new metrics")


def pytest_addoption(parser):
    parser.addoption("--run-latest-metrics", action="store_true", default=False, help="run check_metrics tests")

    if PY2:
        # Add dummy memray options to make it possible to run memray with `ddev test --memray <integration>`
        # in both py2 and 3 environments. In py2 the option is simply ignored, see pytest_collection_modifyitems.
        # In py3 the option enables the memray plugin.
        parser.addoption("--memray", action="store_true", default=False, help="Dummy parameter for memray")
        parser.addoption(
            "--hide-memray-summary",
            action="store_true",
            default=False,
            help="Dummy parameter for memray to hide the summary",
        )


def pytest_collection_modifyitems(config, items):
    # at test collection time, this function gets called by pytest, see:
    # https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
    # if the particular option is not present, it will skip all tests marked `latest_metrics`
    if config.getoption("--run-latest-metrics"):
        # --run-check-metrics given in cli: do not skip slow tests
        return

    if PY2:
        for option in ("--memray",):
            if config.getoption(option):
                warnings.warn(  # noqa: B028
                    "`{}` option ignored as it's not supported for py2 environments.".format(option)
                )  # noqa: B028, E501

    skip_latest_metrics = pytest.mark.skip(reason="need --run-latest-metrics option to run")
    for item in items:
        if "latest_metrics" in item.keywords:
            item.add_marker(skip_latest_metrics)

        # In Python 2 we're using a much older version of pytest where the Item interface is different.
        item_path = item.fspath if PY2 else item.path
        if item_path is None:
            continue
        for ttype in TEST_TYPES:
            if ttype.filepath_match in str(item_path):
                item.add_marker(getattr(pytest.mark, ttype.name))
