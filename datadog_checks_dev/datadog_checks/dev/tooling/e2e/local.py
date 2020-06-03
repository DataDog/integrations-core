# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from contextlib import contextmanager
from shutil import copyfile, move

from ...structures import EnvVars
from ...subprocess import run_command
from ...utils import ON_LINUX, ON_MACOS, ON_WINDOWS, file_exists, path_join
from ..constants import REQUIREMENTS_IN, get_root
from .agent import (
    DEFAULT_AGENT_VERSION,
    DEFAULT_PYTHON_VERSION,
    FAKE_API_KEY,
    MANIFEST_VERSION_PATTERN,
    get_agent_conf_dir,
    get_agent_exe,
    get_agent_service_cmd,
    get_agent_version_manifest,
    get_pip_exe,
    get_rate_flag,
)
from .config import config_file_name, locate_config_dir, locate_config_file, remove_env_data, write_env_data
from .platform import LINUX, MAC, WINDOWS


class LocalAgentInterface(object):
    ENV_TYPE = 'local'

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
        dd_url=None,
        log_url=None,
        python_version=DEFAULT_PYTHON_VERSION,
        default_agent=False,
    ):
        self.check = check
        self.env = env
        self.base_package = base_package
        self.config = config or {}
        # Env vars are not currently used in local E2E
        self.env_vars = env_vars or {}
        self.metadata = metadata or {}
        self.agent_build = agent_build
        self.api_key = api_key or FAKE_API_KEY
        self.dd_url = dd_url
        self.log_url = log_url
        self.python_version = python_version or DEFAULT_PYTHON_VERSION

        self._agent_version = self.metadata.get('agent_version')
        self.config_dir = locate_config_dir(check, env)
        self.config_file = locate_config_file(check, env)
        self.config_file_name = config_file_name(self.check)

        self.env_vars['DD_PYTHON_VERSION'] = str(self.python_version)
        if self.dd_url:
            self.env_vars['DD_DD_URL'] = str(self.dd_url)
        if self.log_url:
            self.env_vars['DD_LOGS_CONFIG_DD_URL'] = str(self.log_url)

    @property
    def platform(self):
        if ON_LINUX:
            return LINUX
        elif ON_MACOS:
            return MAC
        elif ON_WINDOWS:
            return WINDOWS
        else:
            raise Exception("Unsupported OS for Local E2E")

    @property
    def agent_version(self):
        return self._agent_version or DEFAULT_AGENT_VERSION

    @property
    def agent_command(self):
        return get_agent_exe(self.agent_version, platform=self.platform)

    def exec_command(self, command, **kwargs):
        if command.startswith('pip '):
            command = command.replace('pip', ' '.join(get_pip_exe(self.python_version, self.platform)), 1)

        return run_command(command, **kwargs)

    def write_config(self, config=None):
        write_env_data(self.check, self.env, config or self.config, self.metadata)
        self.copy_config_to_local_agent()

    def remove_config(self):
        remove_env_data(self.check, self.env)
        self.remove_config_from_local_agent()

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

    def copy_config_to_local_agent(self):
        conf_dir = get_agent_conf_dir(self.check, self.agent_version, self.platform)
        check_conf_file = os.path.join(conf_dir, f'{self.check}.yaml')
        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir)

        if file_exists(check_conf_file):
            copyfile(check_conf_file, f'{check_conf_file}.bak')

        copyfile(self.config_file, check_conf_file)

    def remove_config_from_local_agent(self):
        check_conf_file = os.path.join(
            get_agent_conf_dir(self.check, self.agent_version, self.platform), f'{self.check}.yaml'
        )
        backup_conf_file = f'{check_conf_file}.bak'
        os.remove(check_conf_file)
        if file_exists(backup_conf_file):
            move(backup_conf_file, check_conf_file)

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
        jmx_list=None,
    ):
        # JMX check
        if jmx_list:
            command = f'{self.agent_command} jmx list {jmx_list}'
        # Classic check
        else:
            command = f'{self.agent_command} check {self.check}'

            if rate:
                command += f' {get_rate_flag(self.agent_version)}'

            # These are only available for Agent 6+
            if times is not None:
                command += f' --check-times {times}'

            if pause is not None:
                command += f' --pause {pause}'

            if delay is not None:
                command += f' --delay {delay}'

            if as_json:
                command += f' --json {as_json}'

            if break_point is not None:
                command += f' --breakpoint {break_point}'

        if log_level is not None:
            command += f' --log-level {log_level}'

        return run_command(command, capture=capture)

    def update_check(self):
        command = get_pip_exe(self.python_version, self.platform)
        path = path_join(get_root(), self.check)
        command.extend(('install', '-e', f'{path}[deps]'))
        return run_command(command, capture=True, check=True)

    def update_base_package(self):
        command = get_pip_exe(self.python_version, self.platform)
        command.extend(('install', '-e', self.base_package))
        command.extend(('-r', path_join(self.base_package, REQUIREMENTS_IN)))
        return run_command(command, capture=True, check=True)

    def update_agent(self):
        # The Local E2E assumes an Agent is already installed on the machine
        pass

    def detect_agent_version(self):
        if self.agent_build and self._agent_version is None:
            with open(get_agent_version_manifest(self.platform)) as f:
                ver = f.readline()
                match = re.search(MANIFEST_VERSION_PATTERN, ver)
            if match:
                self._agent_version = int(match.group(1))

            self.metadata['agent_version'] = self.agent_version

    def start_agent(self):
        with EnvVars(self.env_vars):
            command = get_agent_service_cmd(self.agent_version, self.platform, 'start')

        return run_command(command, capture=True)

    def stop_agent(self):
        command = get_agent_service_cmd(self.agent_version, self.platform, 'stop')
        run_command(command, capture=True)
