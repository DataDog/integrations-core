# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import  # To be able to import docker client

import re
from contextlib import contextmanager
from docker import client as docker_client
from docker.types.services import Mount
from datadog_checks.dev.docker import run_in_container

from ...subprocess import run_command
from ...utils import path_join
from ..constants import get_root
from .agent import (
    DEFAULT_AGENT_VERSION,
    DEFAULT_PYTHON_VERSION,
    FAKE_API_KEY,
    MANIFEST_VERSION_PATTERN,
    get_agent_conf_dir,
    get_agent_exe,
    get_agent_version_manifest,
    get_pip_exe,
    get_rate_flag,
)
from .config import config_file_name, env_exists, locate_config_dir, locate_config_file, remove_env_data, write_env_data


class DockerInterface(object):
    ENV_TYPE = 'docker'

    def __init__(
        self,
        check,
        env,
        base_package=None,
        config=None,
        env_vars=None,
        metadata=None,
        agent_build=None,
        api_key=None,
        python_version=DEFAULT_PYTHON_VERSION,
    ):
        self.check = check
        self.env = env
        self.env_vars = env_vars or {}
        self.base_package = base_package
        self.config = config or {}
        self.metadata = metadata or {}
        self.agent_build = agent_build
        self.api_key = api_key or FAKE_API_KEY
        self.python_version = python_version or DEFAULT_PYTHON_VERSION

        self._agent_version = self.metadata.get('agent_version')
        self.container_name = 'dd_{}_{}'.format(self.check, self.env)
        self.config_dir = locate_config_dir(check, env)
        self.config_file = locate_config_file(check, env)
        self.config_file_name = config_file_name(self.check)

        if self.agent_build and 'py' not in self.agent_build:
            self.agent_build = '{}-py{}'.format(self.agent_build, self.python_version)

        if self.agent_build and self.metadata.get('use_jmx', False):
            self.agent_build = '{}-jmx'.format(self.agent_build)

    @property
    def agent_version(self):
        return self._agent_version or DEFAULT_AGENT_VERSION

    @property
    def check_mount_dir(self):
        return '/home/{}'.format(self.check)

    @property
    def base_mount_dir(self):
        return '/home/datadog_checks_base'

    @property
    def agent_command(self):
        return get_agent_exe(self.agent_version)

    def exec_command(self, command, **kwargs):
        if command.startswith('pip '):
            command = command.replace('pip', ' '.join(get_pip_exe(self.python_version)), 1)
        run_in_container(self.container_name, command, interactive=kwargs.pop('interactive', False))

    def run_check(
        self,
        capture=False,
        rate=False,
        times=None,
        pause=None,
        delay=None,
        log_level=None,
        as_json=False,
        break_point=None,
        jmx_list='matching',
    ):
        # JMX check
        if self.metadata.get('use_jmx', False):
            command = '{} jmx list {}'.format(self.agent_command, jmx_list)
        # Classic check
        else:
            command = '{} check {}'.format(self.agent_command, self.check)

            if rate:
                command += ' {}'.format(get_rate_flag(self.agent_version))

            # These are only available for Agent 6+
            if times is not None:
                command += ' --check-times {}'.format(times)

            if pause is not None:
                command += ' --pause {}'.format(pause)

            if delay is not None:
                command += ' --delay {}'.format(delay)

            if as_json:
                command += ' --json {}'.format(as_json)

            if break_point is not None:
                command += ' --breakpoint {}'.format(break_point)

        if log_level is not None:
            command += ' --log-level {}'.format(log_level)

        return self.exec_command(command, capture=capture, interactive=break_point is not None)

    def exists(self):
        return env_exists(self.check, self.env)

    def remove_config(self):
        remove_env_data(self.check, self.env)

    def write_config(self, config=None):
        write_env_data(self.check, self.env, config or self.config, self.metadata)

    @contextmanager
    def use_config(self, config):
        # Avoid an unnecessary file write if possible
        if config != self.config:
            try:
                self.write_config(config)
                yield
            finally:
                self.write_config()
        else:
            yield

    def detect_agent_version(self):
        if self.agent_build and self._agent_version is None:
            command = [
                'docker',
                'run',
                '--rm',
                '-e',
                'DD_API_KEY={}'.format(self.api_key),
                self.agent_build,
                'head',
                '--lines=1',
                '{}'.format(get_agent_version_manifest('linux')),
            ]
            result = run_command(command, capture=True)
            match = re.search(MANIFEST_VERSION_PATTERN, result.stdout)
            if match:
                self._agent_version = int(match.group(1))

            self.metadata['agent_version'] = self.agent_version

    def update_check(self):
        command = get_pip_exe(self.python_version) + ['install', '-e', self.check_mount_dir]
        run_in_container(self.container_name, command)

    def update_base_package(self):
        command = get_pip_exe(self.python_version) + ['install', '-e', self.base_mount_dir]
        run_in_container(self.container_name, command)

    def update_agent(self):
        if self.agent_build:
            run_command(['docker', 'pull', self.agent_build], capture=True, check=True)

    def start_agent(self):
        if self.agent_build:
            client = docker_client.from_env()
            environment = {
                # Agent 6 will simply fail without an API key
                'DD_API_KEY': self.api_key,
                # Run expvar on a random port
                'DD_EXPVAR_PORT': 0,
                # Run API on a random port
                'DD_CMD_PORT': 0,
                # Disable trace agent
                'DD_APM_ENABLED': 'false',
            }
            volumes = [
                # Mount the config directory, not the file, to ensure updates are propagated
                # https://github.com/moby/moby/issues/15793#issuecomment-135411504
                Mount(source=self.config_dir, target=get_agent_conf_dir(self.check, self.agent_version), type='bind'),
                # Mount the check directory
                Mount(source=path_join(get_root(), self.check), target=self.check_mount_dir, type='bind'),
                # Mount the /proc directory
                Mount(source='/proc', target='/host/proc', type='bind'),
            ]
            for volume in self.metadata.get('docker_volumes', []):
                source, target = volume.split(':')
                volumes.append(Mount(source=source, target=target, type='bind'))

            # Any environment variables passed to the start command
            for key, value in sorted(self.env_vars.items()):
                environment[key] = value

            if self.base_package:
                # Mount the check directory
                volumes.append(Mount(source=self.base_package, target=self.base_mount_dir, type='bind'))

            container = client.containers.run(
                # The chosen tag
                self.agent_build,
                # Keep it up
                detach=True,
                # Ensure consistent naming
                name=self.container_name,
                # Ensure access to host network
                network='host',
                environment=environment,
                mounts=volumes,
            )
            return container

    def stop_agent(self):
        # Only error for exit code if config actually exists
        run_command(['docker', 'stop', self.container_name], capture=True, check=self.exists())
        run_command(['docker', 'rm', self.container_name], capture=True, check=self.exists())

    def restart_agent(self):
        return run_command(['docker', 'restart', self.container_name], capture=True)


def get_docker_networks():
    command = ['docker', 'network', 'ls', '--format', '{{.Name}}']
    lines = run_command(command, capture='out', check=True).stdout.splitlines()

    return [line.strip() for line in lines]
