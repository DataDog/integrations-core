# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from ...subprocess import run_command
from ...utils import path_join
from ..constants import get_root
from .agent import (
    DEFAULT_AGENT_VERSION,
    FAKE_API_KEY,
    MANIFEST_VERSION_PATTERN,
    get_agent_conf_dir,
    get_agent_exe,
    get_agent_version_manifest,
    get_rate_flag,
)
from .config import config_file_name, env_exists, locate_config_dir, locate_config_file, remove_env_data, write_env_data


class DockerInterface(object):
    ENV_TYPE = 'docker'

    def __init__(
        self, check, env, base_package=None, config=None, env_vars=None, metadata=None, agent_build=None, api_key=None
    ):
        self.check = check
        self.env = env
        self.env_vars = env_vars
        self.base_package = base_package
        self.config = config or {}
        self.metadata = metadata or {}
        self.agent_build = agent_build
        self.api_key = api_key or FAKE_API_KEY

        self._agent_version = self.metadata.get('agent_version')
        self.container_name = 'dd_{}_{}'.format(self.check, self.env)
        self.config_dir = locate_config_dir(check, env)
        self.config_file = locate_config_file(check, env)
        self.config_file_name = config_file_name(self.check)

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
        cmd = 'docker exec'

        if kwargs.pop('interactive', False):
            cmd += ' -it'

        cmd += ' {}'.format(self.container_name)
        cmd += ' {}'.format(command)

        return run_command(cmd, **kwargs)

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
    ):
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

        if log_level is not None:
            command += ' --log-level {}'.format(log_level)

        if as_json:
            command += ' --json {}'.format(as_json)

        if break_point is not None:
            command += ' --breakpoint {}'.format(break_point)

        return self.exec_command(command, capture=capture, interactive=break_point is not None)

    def exists(self):
        return env_exists(self.check, self.env)

    def remove_config(self):
        remove_env_data(self.check, self.env)

    def write_config(self):
        write_env_data(self.check, self.env, self.config, self.metadata)

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
        command = ['docker', 'exec', self.container_name, 'pip', 'install', '-e', self.check_mount_dir]
        run_command(command, capture=True, check=True)

    def update_base_package(self):
        command = ['docker', 'exec', self.container_name, 'pip', 'install', '-e', self.base_mount_dir]
        run_command(command, capture=True, check=True)

    def update_agent(self):
        if self.agent_build:
            run_command(['docker', 'pull', self.agent_build], capture=True, check=True)

    def start_agent(self):
        if self.agent_build:
            command = [
                'docker',
                'run',
                # Keep it up
                '-d',
                # Ensure consistent naming
                '--name',
                self.container_name,
                # Ensure access to host network
                '--network',
                'host',
                # Agent 6 will simply fail without an API key
                '-e',
                'DD_API_KEY={}'.format(self.api_key),
                # Mount the config directory, not the file, to ensure updates are propagated
                # https://github.com/moby/moby/issues/15793#issuecomment-135411504
                '-v',
                '{}:{}'.format(self.config_dir, get_agent_conf_dir(self.check, self.agent_version)),
                # Mount the check directory
                '-v',
                '{}:{}'.format(path_join(get_root(), self.check), self.check_mount_dir),
                # Mount the /proc directory
                '-v',
                '/proc:/host/proc',
            ]

            # Any environment variables passed to the start command
            command.extend('-e {}'.format(var) for var in self.env_vars)

            if self.base_package:
                # Mount the check directory
                command.append('-v')
                command.append('{}:{}'.format(self.base_package, self.base_mount_dir))

            # The chosen tag
            command.append(self.agent_build)

            return run_command(command, capture=True)

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
