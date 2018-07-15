# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import time
from contextlib import contextmanager

from six import string_types
from six.moves.urllib.error import URLError
from six.moves.urllib.parse import urlparse
from six.moves.urllib.request import urlopen

from ._env import tear_down_env
from .errors import RetryError
from .structures import EnvVars, LazyFunction
from .subprocess import run_command
from .utils import mock_context_manager


def get_docker_hostname():
    return urlparse(os.getenv('DOCKER_HOST', '')).hostname or 'localhost'


def get_container_ip(container_id_or_name):
    """Get a Docker container's IP address from its id or name."""
    command = [
        'docker',
        'inspect',
        '-f',
        '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id_or_name
    ]

    return run_command(command, capture='out', check=True).stdout.strip()


def compose_file_active(compose_file):
    command = ['docker-compose', '-f', compose_file, 'ps']
    lines = run_command(command, capture='out', check=True).stdout.splitlines()

    for i, line in enumerate(lines, 1):
        if set(line.strip()) == {'-'}:
            return len(lines[i:]) >= 1

    return False


@contextmanager
def docker_run(
    compose_file=None,
    up=None,
    down=None,
    endpoints=None,
    log_patterns=None,
    conditions=None,
    env_vars=None,
    wrapper=None
):
    if compose_file is not None and up is not None:
        raise TypeError('You must select either a compose file or a custom spin up callable, not both.')

    if compose_file is not None:
        if not isinstance(compose_file, string_types):
            raise TypeError('The path to the compose file must be a string.')
        spin_up = ComposeFileUp(compose_file)
        tear_down = ComposeFileDown(compose_file)
    elif up is not None:
        if not callable(up):
            raise TypeError('The custom spin up must be callable.')
        elif down is None:
            raise ValueError('A custom tear down must be selected when using a custom spin up.')
        elif not callable(down):
            raise TypeError('The custom tear down must be callable.')
        spin_up = up
        tear_down = down
    else:
        raise TypeError('You must select either a compose file or a custom spin up callable.')

    conditions = list(conditions) if conditions is not None else []

    if log_patterns is not None:
        if compose_file is None:
            raise ValueError(
                'The `log_patterns` convenience is unavailable when using '
                'a custom spin up. Please use a custom condition instead.'
            )
        conditions.append(CheckComposeFileLogs(compose_file, log_patterns))

    if endpoints is not None:
        conditions.append(CheckEndpoints(endpoints))

    env_vars = mock_context_manager() if env_vars is None else EnvVars(env_vars)
    wrapper = mock_context_manager() if wrapper is None else wrapper

    with env_vars, wrapper:
        try:
            result = spin_up()
            for condition in conditions:
                condition()
            yield result
        finally:
            if tear_down_env():
                tear_down()


class ComposeFileUp(LazyFunction):
    def __init__(self, compose_file, service_name=None):
        self.compose_file = compose_file
        self.service_name = service_name
        self.command = ['docker-compose', '-f', self.compose_file, 'up', '-d']
        if self.service_name:
            self.command.append(self.service_name)

    def __call__(self):
        return run_command(self.command, check=True)


class ComposeFileDown(LazyFunction):
    def __init__(self, compose_file, check=True):
        self.compose_file = compose_file
        self.check = check
        self.command = ['docker-compose', '-f', self.compose_file, 'down']

    def __call__(self):
        return run_command(self.command, check=self.check)


class CheckEndpoints(LazyFunction):
    def __init__(self, endpoints, timeout=1, attempts=60, wait=1):
        self.endpoints = endpoints
        self.timeout = timeout
        self.attempts = attempts
        self.wait = wait

    def __call__(self):
        last_endpoint = ''
        last_error = ''

        for _ in range(self.attempts):
            for endpoint in self.endpoints:
                last_endpoint = endpoint
                try:
                    request = urlopen(endpoint, timeout=self.timeout)
                except URLError as e:
                    last_error = str(e)
                    break
                else:
                    status_code = request.getcode()
                    if 400 <= status_code < 600:
                        last_error = 'status {}'.format(status_code)
                        break
            else:
                break

            time.sleep(self.wait)
        else:
            raise RetryError(
                'Endpoint: {}\n'
                'Error: {}'.format(
                    last_endpoint,
                    last_error
                )
            )


class CheckComposeFileLogs(LazyFunction):
    def __init__(self, compose_file, patterns, matches=1, attempts=60, wait=1):
        self.compose_file = compose_file
        self.attempts = attempts
        self.wait = wait
        self.command = ['docker-compose', '-f', self.compose_file, 'logs']

        if matches == 'all':
            self.matches = len(patterns)
        else:
            self.matches = matches

        self.patterns = [
            re.compile(pattern, re.M) if isinstance(pattern, string_types) else pattern
            for pattern in patterns
        ]

    def __call__(self):
        log_output = ''

        for _ in range(self.attempts):
            result = run_command(self.command, capture=True, check=True)
            log_output = result.stdout
            matches = 0

            for pattern in self.patterns:
                if pattern.search(log_output):
                    matches += 1

            if matches >= self.matches:
                break

            time.sleep(self.wait)
        else:
            raise RetryError(
                'Command: {}\n'
                'Captured Output: {}'.format(
                    self.command,
                    log_output
                )
            )


class CheckContainerLogs(LazyFunction):
    def __init__(self, container_name, patterns, matches=1, attempts=60, wait=1):
        self.container_name = container_name
        self.attempts = attempts
        self.wait = wait
        self.command = ['docker', 'logs', container_name]

        if matches == 'all':
            self.matches = len(patterns)
        else:
            self.matches = matches

        self.patterns = [
            re.compile(pattern, re.M) if isinstance(pattern, string_types) else pattern
            for pattern in patterns
        ]

    def __call__(self):
        log_output = ''

        for _ in range(self.attempts):
            result = run_command(self.command, capture=True, check=True)
            log_output = result.stdout
            matches = 0

            for pattern in self.patterns:
                if pattern.search(log_output):
                    matches += 1

            if matches >= self.matches:
                break

            time.sleep(self.wait)
        else:
            raise RetryError(
                'Command: {}\n'
                'Captured Output: {}'.format(
                    self.command,
                    log_output
                )
            )
