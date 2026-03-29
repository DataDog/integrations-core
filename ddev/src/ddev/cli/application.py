# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import re
from functools import cached_property
from typing import cast

from ddev.cli.terminal import Terminal
from ddev.config.constants import AppEnvVars, ConfigEnvVars, VerbosityLevels
from ddev.config.file import ConfigFileWithOverrides, RootConfig
from ddev.config.model import ConfigurationError
from ddev.repo.core import Repository
from ddev.utils.fs import Path
from ddev.utils.github import GitHubManager
from ddev.utils.platform import Platform

_SECRET_RESOLUTION_ERROR_PATTERN = re.compile(
    r'\[(?P<code>[^\]]+)\]\s+could not resolve required secret for (?P<field_path>[^;]+);\s+'
    r'sources\(command=(?P<command>[^,]+),\s*literal=(?P<literal>[^,]+),\s*env=(?P<environment>[^)]+)\);\s*'
    r'(?P<remediation>.+)$'
)


def format_secret_resolution_error(error: ConfigurationError) -> str | None:
    """Return an actionable secret error summary, or None if the error is unrelated."""
    match = _SECRET_RESOLUTION_ERROR_PATTERN.search(str(error))
    if match is None:
        return None

    details = match.groupdict()
    code = details['code']
    field_path = details['field_path']
    command = details['command']
    literal = details['literal']
    environment = details['environment']
    remediation = details['remediation']

    if code == 'missing-required-secret':
        message_lines = [f'Missing required secret: {field_path}']
    else:
        message_lines = [f'Failed to resolve required secret: {field_path}']

    message_lines.extend(
        [
            f'Code: {code}',
            f'Sources: command={command}, literal={literal}, env={environment}',
            f'Remediation: {remediation}',
        ]
    )

    if command == 'blocked-untrusted-local-config':
        message_lines.append(
            'Trust workflow: run `ddev config allow` to trust the current local config content, '
            'or run `ddev config deny` to clear trust records.'
        )

    return '\n'.join(message_lines)


class Application(Terminal):
    def __init__(self, exit_func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform = Platform(self.escaped_output)
        self.__exit_func = exit_func

        self.config_file = ConfigFileWithOverrides()
        self.quiet = self.verbosity < VerbosityLevels.INFO
        self.verbose = self.verbosity > VerbosityLevels.INFO

        # Lazily set these as we acquire more knowledge about the desired environment
        self.__repo = cast(Repository, None)
        self.__github = cast(GitHubManager, None)

        # TODO: remove this when the old CLI is gone
        self.__config = {}

    @property
    def config(self) -> RootConfig:
        return self.config_file.combined_model

    @property
    def repo(self) -> Repository:
        return self.__repo

    @cached_property
    def data_dir(self) -> Path:
        from platformdirs import user_data_dir

        return Path(os.getenv(ConfigEnvVars.DATA) or user_data_dir('ddev', appauthor=False)).expand()

    @property
    def github(self) -> GitHubManager:
        if self.__github is None:
            try:
                self.__github = GitHubManager(
                    self.repo, user=self.config.github.user, token=self.config.github.token, status=self.status
                )
            except ConfigurationError as e:
                if formatted := format_secret_resolution_error(e):
                    self.abort(formatted)
                raise
        return self.__github

    def set_repo(self, core: bool, extras: bool, marketplace: bool, agent: bool, here: bool):
        # Config looks like this:
        #
        # repo = "core"
        # [repos]
        # core = "~/dd/integrations-core"
        # extras = "~/dd/integrations-extras"
        # marketplace = "~/dd/marketplace"
        # agent = "~/dd/datadog-agent"
        if core:
            self.__repo = Repository('core', self.config.repos['core'])
        elif extras:
            self.__repo = Repository('extras', self.config.repos['extras'])
        elif marketplace:
            self.__repo = Repository('marketplace', self.config.repos['marketplace'])
        elif agent:
            self.__repo = Repository('agent', self.config.repos['agent'])
        elif here:
            self.__repo = Repository('local', str(Path.cwd()))
        elif repo := os.environ.get(AppEnvVars.REPO, ''):
            self.__repo = Repository(repo, self.config.repos[repo])
        else:
            self.__repo = Repository(self.config.repo.name, self.config.repo.path)

    def abort(self, text='', code=1, **kwargs):
        if text:
            self.display_error(text, **kwargs)
        self.__exit_func(code)

    # TODO: remove everything below when the old CLI is gone
    def initialize_old_cli(self):
        from copy import deepcopy

        from datadog_checks.dev.tooling.utils import initialize_root

        self.__config.update(deepcopy(self.config.raw_data))
        self.__config['color'] = not self.console.no_color
        self.__config['dd_api_key'] = self.config.orgs.get('default', {}).get('api_key', '')
        self.__config['dd_app_key'] = self.config.orgs.get('default', {}).get('app_key', '')
        # Provide literal github config for old CLI commands without executing secret commands.
        # Token resolution via *_command is a new-CLI feature; old CLI gets the raw value + env var.
        github_raw = self.config.raw_data.get('github', {})
        self.__config['github'] = {
            'user': github_raw.get('user', '')
            or os.getenv('DD_GITHUB_USER', '')
            or os.getenv('GITHUB_USER', '')
            or os.getenv('GITHUB_ACTOR', ''),
            'token': github_raw.get('token', '')
            or os.getenv('DD_GITHUB_TOKEN', '')
            or os.getenv('GH_TOKEN', '')
            or os.getenv('GITHUB_TOKEN', ''),
        }
        # Make sure that envvar overrides of repo make it into config.
        self.__config['repo'] = self.repo.name
        # Transfer the -x/--here flag to the old CLI.
        # In the new CLI that flag turns into a repo named "local" but the old CLI expects a bool kwarg "here".
        kwargs = {}
        if self.repo.name == 'local':
            kwargs['here'] = True
        initialize_root(self.__config, **kwargs)

    def copy(self):
        return self.__config.copy()

    def get(self, key, *args, **kwargs):
        return self.__config.get(key, *args, **kwargs)

    def pop(self, key, *args, **kwargs):
        return self.__config.get(key, *args, **kwargs)

    def __getitem__(self, item):
        return self.__config[item]

    def __setitem__(self, key, value):
        self.__config[key] = value
