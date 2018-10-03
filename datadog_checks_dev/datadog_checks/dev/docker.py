# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from contextlib import contextmanager

from six import string_types
from six.moves.urllib.parse import urlparse

from ._env import set_up_env, tear_down_env
from .conditions import CheckDockerLogs, CheckEndpoints
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
    build=False,
    service_name=None,
    up=None,
    down=None,
    sleep=None,
    endpoints=None,
    log_patterns=None,
    conditions=None,
    env_vars=None,
    wrapper=None
):
    """This utility provides a convenient way to safely set up and tear down Docker environments.

    :param compose_file: A path to a Docker compose file. A custom tear
                         down is not required when using this.
    :type compose_file: ``str``
    :param build: Whether or not to build images for when ``compose_file`` is provided.
    :type build: ``bool``
    :param service_name: Optional name for when ``compose_file`` is provided.
    :type service_name: ``str``
    :param up: A custom setup callable.
    :type up: ``callable``
    :param down: A custom tear down callable. This is required when using a custom setup.
    :type down: ``callable``
    :param sleep: Number of seconds to wait before yielding.
    :type sleep: ``float``
    :param endpoints: Endpoints to verify access for before yielding. Shorthand for adding
                      ``conditions.CheckEndpoints(endpoints)`` to the ``conditions`` argument.
    :type endpoints: ``list`` of ``str``, or a single ``str``
    :param log_patterns: Patterns to find in Docker logs before yielding. This is only available
                         when ``compose_file`` is provided. Shorthand for adding
                         ``conditions.CheckDockerLogs(compose_file, log_patterns)`` to the ``conditions`` argument.
    :type log_patterns: ``list`` of (``str`` or ``re.Pattern``)
    :param conditions: A list of callable objects that will be executed before yielding to check for errors.
    :type conditions: ``callable``
    :param env_vars: A dictionary to update ``os.environ`` with during execution.
    :type env_vars: ``dict``
    :param wrapper: A context manager to use during execution.
    """
    if compose_file and up:
        raise TypeError('You must select either a compose file or a custom setup callable, not both.')

    if compose_file is not None:
        if not isinstance(compose_file, string_types):
            raise TypeError('The path to the compose file must be a string.')
        set_up = ComposeFileUp(compose_file, build=build, service_name=service_name)
        if down is not None:
            if not callable(down):
                raise TypeError('The custom tear down must be callable.')
            tear_down = down
        else:
            tear_down = ComposeFileDown(compose_file)
    elif up is not None:
        if not callable(up):
            raise TypeError('The custom setup must be callable.')
        elif down is None:
            raise ValueError('A custom tear down must be selected when using a custom setup.')
        elif not callable(down):
            raise TypeError('The custom tear down must be callable.')
        set_up = up
        tear_down = down
    else:
        raise TypeError('You must select either a compose file or a custom setup callable.')

    conditions = list(conditions) if conditions is not None else []

    if log_patterns is not None:
        if compose_file is None:
            raise ValueError(
                'The `log_patterns` convenience is unavailable when using '
                'a custom setup. Please use a custom condition instead.'
            )
        conditions.append(CheckDockerLogs(compose_file, log_patterns))

    if endpoints is not None:
        conditions.append(CheckEndpoints(endpoints))

    env_vars = mock_context_manager() if env_vars is None else EnvVars(env_vars)
    wrapper = mock_context_manager() if wrapper is None else wrapper

    result = None
    with env_vars, wrapper:
        try:
            if set_up_env():
                result = set_up()

                for condition in conditions:
                    condition()

                if sleep:
                    time.sleep(sleep)

            yield result
        finally:
            if tear_down_env():
                tear_down()


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


class ComposeFileDown(LazyFunction):
    def __init__(self, compose_file, check=True):
        self.compose_file = compose_file
        self.check = check
        self.command = ['docker-compose', '-f', self.compose_file, 'down']

    def __call__(self):
        return run_command(self.command, check=self.check)
