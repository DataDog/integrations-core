# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import contextmanager
from typing import Iterator

from six import string_types
from six.moves.urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_fixed

from .conditions import CheckDockerLogs
from .env import environment_run, get_state, save_state
from .spec import load_spec
from .structures import EnvVars, LazyFunction, TempDir
from .subprocess import run_command
from .utils import create_file, file_exists, find_check_root

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


def get_docker_hostname():
    """
    Determine the hostname Docker uses based on the environment, defaulting to `localhost`.
    """
    return urlparse(os.getenv('DOCKER_HOST', '')).hostname or 'localhost'


def get_container_ip(container_id_or_name):
    """
    Get a Docker container's IP address from its ID or name.
    """
    command = [
        'docker',
        'inspect',
        '-f',
        '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id_or_name,
    ]

    return run_command(command, capture='out', check=True).stdout.strip()


def compose_file_active(compose_file):
    """
    Returns a `bool` indicating whether or not a compose file has any active services.
    """
    command = ['docker-compose', '-f', compose_file, 'ps']
    lines = run_command(command, capture='out', check=True).stdout.splitlines()

    for i, line in enumerate(lines, 1):
        if set(line.strip()) == {'-'}:
            return len(lines[i:]) >= 1

    return False


@contextmanager
def shared_logs(example_log_configs, mount_whitelist=None):
    log_source = example_log_configs[0].get('source', 'check')

    if mount_whitelist is None:
        # Default to all
        mount_whitelist = range(1, len(example_log_configs) + 1)

    env_vars = {}
    docker_volumes = get_state('docker_volumes', [])

    with ExitStack() as stack:
        for i, example_log_config in enumerate(example_log_configs, 1):
            if i not in mount_whitelist:
                continue

            log_name = 'dd_log_{}'.format(i)
            d = stack.enter_context(TempDir(log_name))

            # Create the file that will ultimately be shared by containers
            shared_log_file = os.path.join(d, '{}_{}.log'.format(log_source, log_name))
            if not file_exists(shared_log_file):
                create_file(shared_log_file)

            # Set config to the path in the Agent
            agent_mount_path = '/var/log/{}/{}'.format(log_source, log_name)
            example_log_config['path'] = agent_mount_path
            docker_volumes.append('{}:{}'.format(shared_log_file, agent_mount_path))

            # If service is the default, use the source
            if example_log_config.get('service', '<SERVICE>') == '<SERVICE>':
                example_log_config['service'] = log_source

            # Make it available to reference for Docker volumes
            env_vars[log_name.upper()] = shared_log_file

        # Inject and persist this data for `env test` & `env stop`
        save_state('logs_config', example_log_configs)
        save_state('docker_volumes', docker_volumes)

        with EnvVars(env_vars):
            yield


@contextmanager
def docker_run(
    compose_file=None,
    build=False,
    service_name=None,
    up=None,
    down=None,
    on_error=None,
    sleep=None,
    endpoints=None,
    log_patterns=None,
    mount_logs=False,
    conditions=None,
    env_vars=None,
    wrappers=None,
    attempts=None,
    attempts_wait=1,
):
    """
    A convenient context manager for safely setting up and tearing down Docker environments.

    - **compose_file** (_str_) - A path to a Docker compose file. A custom tear
      down is not required when using this.
    - **build** (_bool_) - Whether or not to build images for when `compose_file` is provided
    - **service_name** (_str_) - Optional name for when ``compose_file`` is provided
    - **up** (_callable_) - A custom setup callable
    - **down** (_callable_) - A custom tear down callable. This is required when using a custom setup.
    - **on_error** (_callable_) - A callable called in case of an unhandled exception
    - **sleep** (_float_) - Number of seconds to wait before yielding. This occurs after all conditions are successful.
    - **endpoints** (_List[str]_) - Endpoints to verify access for before yielding. Shorthand for adding
      `CheckEndpoints(endpoints)` to the `conditions` argument.
    - **log_patterns** (_List[str|re.Pattern]_) - Regular expression patterns to find in Docker logs before yielding.
      This is only available when `compose_file` is provided. Shorthand for adding
      `CheckDockerLogs(compose_file, log_patterns)` to the `conditions` argument.
    - **mount_logs** (_bool_) - Whether or not to mount log files in Agent containers based on example logs
      configuration
    - **conditions** (_callable_) - A list of callable objects that will be executed before yielding to
      check for errors
    - **env_vars** (_dict_) - A dictionary to update `os.environ` with during execution
    - **wrappers** (_List[callable]_) - A list of context managers to use during execution
    - **attempts** (_int_) - Number of attempts to run `up` successfully
    - **attempts_wait** (_int_) - Time to wait between attempts
    """
    if compose_file and up:
        raise TypeError('You must select either a compose file or a custom setup callable, not both.')

    if compose_file is not None:
        if not isinstance(compose_file, string_types):
            raise TypeError('The path to the compose file is not a string: {}'.format(repr(compose_file)))

        set_up = ComposeFileUp(compose_file, build=build, service_name=service_name)
        if down is not None:
            tear_down = down
        else:
            tear_down = ComposeFileDown(compose_file)
        if on_error is None:
            on_error = ComposeFileLogs(compose_file)
    else:
        set_up = up
        tear_down = down

    if attempts is not None:
        saved_set_up = set_up

        @retry(wait=wait_fixed(attempts_wait), stop=stop_after_attempt(attempts))
        def set_up_with_retry():
            return saved_set_up()

        set_up = set_up_with_retry

    docker_conditions = []

    if log_patterns is not None:
        if compose_file is None:
            raise ValueError(
                'The `log_patterns` convenience is unavailable when using '
                'a custom setup. Please use a custom condition instead.'
            )
        docker_conditions.append(CheckDockerLogs(compose_file, log_patterns))

    if conditions is not None:
        docker_conditions.extend(conditions)

    wrappers = list(wrappers) if wrappers is not None else []

    if mount_logs:
        if isinstance(mount_logs, dict):
            wrappers.append(shared_logs(mount_logs['logs']))
        # Easy mode, read example config
        else:
            # An extra level deep because of the context manager
            check_root = find_check_root(depth=2)

            example_log_configs = _read_example_logs_config(check_root)
            if mount_logs is True:
                wrappers.append(shared_logs(example_log_configs))
            elif isinstance(mount_logs, (list, set)):
                wrappers.append(shared_logs(example_log_configs, mount_whitelist=mount_logs))
            else:
                raise TypeError(
                    'mount_logs: expected True, a list or a set, but got {}'.format(type(mount_logs).__name__)
                )

    with environment_run(
        up=set_up,
        down=tear_down,
        on_error=on_error,
        sleep=sleep,
        endpoints=endpoints,
        conditions=docker_conditions,
        env_vars=env_vars,
        wrappers=wrappers,
    ) as result:
        yield result


class ComposeFileUp(LazyFunction):
    def __init__(self, compose_file, build=False, service_name=None):
        self.compose_file = compose_file
        self.build = build
        self.service_name = service_name
        self.command = ['docker-compose', '-f', self.compose_file, 'up', '-d']

        if self.build:
            self.command.append('--build')

        if self.service_name:
            self.command.append(self.service_name)

    def __call__(self):
        return run_command(self.command, check=True)


class ComposeFileLogs(LazyFunction):
    def __init__(self, compose_file, check=True):
        self.compose_file = compose_file
        self.check = check
        self.command = ['docker-compose', '-f', self.compose_file, 'logs']

    def __call__(self, exception):
        return run_command(self.command, capture=False, check=self.check)


class ComposeFileDown(LazyFunction):
    def __init__(self, compose_file, check=True):
        self.compose_file = compose_file
        self.check = check
        self.command = ['docker-compose', '-f', self.compose_file, 'down', '--volumes', '--remove-orphans', '-t', '0']

    def __call__(self):
        return run_command(self.command, check=self.check)


def _read_example_logs_config(check_root):
    spec = load_spec(check_root)

    for f in spec['files']:
        for option in f['options']:
            if option.get('template') == 'logs':
                return option['example']

    raise ValueError('No logs example found')


@contextmanager
def temporarily_stop_service(service, compose_file, check=True):
    # type: (str, str, bool) -> Iterator[None]
    run_command(['docker-compose', '-f', compose_file, 'stop', service], capture=False, check=check)
    yield
    run_command(['docker-compose', '-f', compose_file, 'start', service], capture=False, check=check)
