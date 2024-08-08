# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import re
import sys
from contextlib import AbstractContextManager, contextmanager, nullcontext
from functools import cache, cached_property, partial
from typing import TYPE_CHECKING, Callable, Type

import stamina

from ddev.e2e.agent.interface import AgentInterface
from ddev.utils.structures import EnvVars

if TYPE_CHECKING:
    import subprocess

    from ddev.utils.fs import Path

AGENT_VERSION_REGEX = r'^datadog/agent:\d+(?:$|\.(\d+\.\d(?:$|-jmx$)|$))'


@contextmanager
def disable_integration_before_install(config_file):
    """
    Disable integration by renaming the config to "conf.yaml.example".

    As we exit the context manager we rename it back to "conf.yaml" to re-enable the integration.
    """

    old = config_file.name
    new = config_file.rename(config_file.parent / (config_file.name + ".example"))
    yield
    new.rename(config_file.parent / old)


class DockerAgent(AgentInterface):
    @cached_property
    def _isatty(self) -> bool:
        isatty: Callable[[], bool] | None = getattr(sys.stdout, 'isatty', None)
        if isatty is not None:
            try:
                return isatty()
            except ValueError:
                pass

        return False

    @cached_property
    def _container_name(self) -> str:
        return f'dd_{super().get_id()}'

    @cached_property
    def _is_windows_container(self) -> bool:
        return self.metadata.get('docker_platform') == 'windows'

    @cached_property
    def _package_mount_dir(self) -> str:
        return 'C:\\Users\\ContainerAdministrator\\' if self._is_windows_container else '/home/'

    @cached_property
    def _config_mount_dir(self) -> str:
        return (
            f'C:\\ProgramData\\Datadog\\conf.d\\{self.integration.name}.d'
            if self._is_windows_container
            else f'/etc/datadog-agent/conf.d/{self.integration.name}.d'
        )

    @cached_property
    def _python_path(self) -> str:
        return (
            f'C:\\Program Files\\Datadog\\Datadog Agent\\embedded{self.python_version[0]}\\python.exe'
            if self._is_windows_container
            else f'/opt/datadog-agent/embedded/bin/python{self.python_version[0]}'
        )

    def _format_command(self, command: list[str]) -> list[str]:
        cmd = ['docker', 'exec']
        if self._isatty:
            cmd.append('-it')
        cmd.append(self._container_name)

        if command[0] == 'pip':
            command = command[1:]
            cmd.extend([self._python_path, '-m', 'pip'])

        cmd.extend(command)
        return cmd

    def _captured_process(self, command: list[str]) -> subprocess.CompletedProcess:
        return self._run_command(
            command, stdout=self.platform.modules.subprocess.PIPE, stderr=self.platform.modules.subprocess.STDOUT
        )

    def _run_command(self, command: list[str], **kwargs) -> subprocess.CompletedProcess:
        with EnvVars({'DOCKER_CLI_HINTS': 'false'}):
            return self.platform.run_command(command, **kwargs)

    def _show_logs(self) -> None:
        self._run_command(['docker', 'logs', self._container_name])

    def get_id(self) -> str:
        return self._container_name

    def start(self, *, agent_build: str, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None:
        from ddev.e2e.agent.constants import AgentEnvVars

        if not agent_build:
            agent_build = 'datadog/agent-dev:master'

        if agent_build.startswith("datadog/"):
            # Add a potentially missing `py` suffix for default non-RC builds
            if 'rc' not in agent_build and 'py' not in agent_build and not re.match(AGENT_VERSION_REGEX, agent_build):
                agent_build = f'{agent_build}-py{self.python_version[0]}'

            if self.metadata.get('use_jmx') and not agent_build.endswith('-jmx'):
                agent_build += '-jmx'

        env_vars = env_vars.copy()

        # Containerized agents require an API key to start
        if AgentEnvVars.API_KEY not in env_vars:
            # This fake key must be the proper length
            env_vars[AgentEnvVars.API_KEY] = 'a' * 32

        # Set Agent hostname for CI
        env_vars[AgentEnvVars.HOSTNAME] = _get_hostname()

        # Run API on a random free port
        env_vars[AgentEnvVars.CMD_PORT] = str(_find_free_port())

        # Disable trace Agent
        env_vars[AgentEnvVars.APM_ENABLED] = 'false'

        # Set up telemetry
        env_vars[AgentEnvVars.TELEMETRY_ENABLED] = '1'
        env_vars[AgentEnvVars.EXPVAR_PORT] = '5000'

        # TODO: Remove this when Python 2 support is removed
        #
        # Don't write .pyc, needed to fix this issue (only Python 2):
        # More info: https://github.com/DataDog/integrations-core/pull/5454
        # When reinstalling a package, .pyc are not cleaned correctly. The issue is fixed by not writing them
        # in the first place.
        env_vars['PYTHONDONTWRITEBYTECODE'] = '1'

        if (proxy_data := self.metadata.get('proxy')) is not None:
            if (http_proxy := proxy_data.get('http')) is not None:
                env_vars[AgentEnvVars.PROXY_HTTP] = http_proxy
            if (https_proxy := proxy_data.get('https')) is not None:
                env_vars[AgentEnvVars.PROXY_HTTPS] = https_proxy

        volumes = []

        if not self._is_windows_container:
            volumes.append('/proc:/host/proc')

        ensure_local_pkg: Type[AbstractContextManager] | Callable[[], AbstractContextManager] = nullcontext
        # Only mount the volume if the initial configuration is not set to `None`.
        # As an example, the way SNMP does autodiscovery is that the Agent writes what its listener detects
        # in `auto_conf.yaml`. The issue is we mount the entire config directory so changes are always in
        # sync and, unlike other integrations that support autodiscovery, that file doesn't already exist.
        # For that setup it seems the Agent cannot write to a file that does not already exist inside a
        # directory that is mounted.
        if self.config_file.is_file():
            volumes.append(f'{self.config_file.parent}:{self._config_mount_dir}')
            if local_packages:
                # We only want to enable the integration after we install it from a local package.
                # That's because we've come across cases where the integration shipped with the agent image crashes
                # the agent container before we can install a local version that contains a fix.
                # We disable it when we start the agent container, then re-enable it before we restart the container
                # which by then has the version from a local package.
                ensure_local_pkg = partial(disable_integration_before_install, self.config_file)

        # It is safe to assume that the directory name is unique across all repos
        for local_package in local_packages:
            volumes.append(f'{local_package}:{self._package_mount_dir}{local_package.name}')

        volumes.extend(self.metadata.get('docker_volumes', []))

        if self.platform.windows and not self._is_windows_container:
            for i, volume in enumerate(volumes):
                parts = volume.split(':')
                possible_file = ':'.join(parts[:2])
                if os.path.isfile(possible_file):
                    # Workaround for https://github.com/moby/moby/issues/30555
                    vm_file = possible_file.replace(':', '', 1).replace('\\', '/')
                    remaining = ':'.join(parts[2:])
                    volumes[i] = f'/{vm_file}:{remaining}'

        if os.getenv('DDEV_E2E_DOCKER_NO_PULL') != '1':
            self.__pull_image(agent_build)

        command = [
            'docker',
            'run',
            # Keep it up
            '-d',
            # Ensure consistent naming
            '--name',
            self._container_name,
        ]

        # Ensure access to host network
        #
        # Windows containers accessing the host network must use `docker.for.win.localhost` or `host.docker.internal`:
        # https://docs.docker.com/docker-for-windows/networking/#use-cases-and-workarounds
        if not self._is_windows_container:
            command.extend(['--network', 'host'])

        for volume in volumes:
            command.extend(['-v', volume])

        # Any environment variables passed to the start command in addition to the default ones
        for key, value in sorted(env_vars.items()):
            command.extend(['-e', f'{key}={value}'])

        # The docker `--add-host` command will reliably create entries in the `/etc/hosts` file,
        # otherwise, edits to that file will be overwritten on container restarts
        for host, ip in self.metadata.get('custom_hosts', []):
            command.extend(['--add-host', f'{host}:{ip}'])

        if dogstatsd_port := env_vars.get(AgentEnvVars.DOGSTATSD_PORT):
            command.extend(['-p', f'{dogstatsd_port}:{dogstatsd_port}/udp'])

        # The chosen tag
        command.append(agent_build)

        start_commands = self.metadata.get('start_commands', [])
        post_install_commands = self.metadata.get('post_install_commands', [])
        with ensure_local_pkg():
            self._initialize(command, local_packages, start_commands, post_install_commands)

        if local_packages or start_commands or post_install_commands:
            self.restart()

    def _initialize(self, command, local_packages, start_commands, post_install_commands):
        process = self._captured_process(command)
        if process.returncode:
            raise RuntimeError(
                f'Unable to start Agent container `{self._container_name}`: {process.stdout.decode("utf-8")}'
            )

        if start_commands:
            for start_command in start_commands:
                formatted_command = self._format_command(self.platform.modules.shlex.split(start_command))
                process = self._run_command(formatted_command)
                if process.returncode:
                    self._show_logs()
                    raise RuntimeError(f'Unable to run start-up command in Agent container `{self._container_name}`')

        if local_packages:
            base_pip_command = self._format_command(
                [self._python_path, '-m', 'pip', 'install', '--disable-pip-version-check', '-e']
            )
            for local_package, features in local_packages.items():
                package_mount = f'{self._package_mount_dir}{local_package.name}{features}'
                process = self._run_command([*base_pip_command, package_mount])
                if process.returncode:
                    self._show_logs()
                    raise RuntimeError(
                        f'Unable to install package `{local_package.name}` in Agent container '
                        f'`{self._container_name}`'
                    )

        if post_install_commands:
            for post_install_command in post_install_commands:
                formatted_command = self._format_command(self.platform.modules.shlex.split(post_install_command))
                process = self._run_command(formatted_command)
                if process.returncode:
                    self._show_logs()
                    raise RuntimeError(
                        f'Unable to run post-install command in Agent container `{self._container_name}`'
                    )

    def stop(self) -> None:
        stop_commands = self.metadata.get('stop_commands', [])
        if stop_commands:
            for stop_command in stop_commands:
                formatted_command = self._format_command(self.platform.modules.shlex.split(stop_command))
                process = self._run_command(formatted_command)
                if process.returncode:
                    self._show_logs()
                    raise RuntimeError(f'Unable to run stop command in Agent container `{self._container_name}`')

        for command in (
            ['docker', 'stop', '-t', '0', self._container_name],
            # Remove manually rather than using the `--rm` flag of the `run` command to allow for
            # debugging issues that caused the Agent container to stop
            ['docker', 'rm', self._container_name],
        ):
            process = self._captured_process(command)
            if process.returncode:
                raise RuntimeError(
                    f'Unable to stop Agent container `{self._container_name}`: {process.stdout.decode("utf-8")}'
                )

    def restart(self) -> None:
        process = self._captured_process(['docker', 'restart', self._container_name])
        if process.returncode:
            raise RuntimeError(
                f'Unable to restart Agent container `{self._container_name}`: {process.stdout.decode("utf-8")}'
            )

    def invoke(self, args: list[str]) -> None:
        self.run_command(['agent', *args])

    def run_command(self, args: list[str]) -> None:
        self._run_command(self._format_command([*args]), check=True)

    def enter_shell(self) -> None:
        self._run_command(self._format_command(['cmd' if self._is_windows_container else 'bash']), check=True)

    @stamina.retry(on=RuntimeError, attempts=3)
    def __pull_image(self, agent_build):
        process = self._run_command(['docker', 'pull', agent_build])
        if process.returncode:
            raise RuntimeError(f'Could not pull image {agent_build}')


@cache
def _get_hostname():
    import socket

    return socket.gethostname().lower()


def _find_free_port():
    import socket
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        # doesn't have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((ip, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
