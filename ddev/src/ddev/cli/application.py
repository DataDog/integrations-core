# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
import os
from collections import defaultdict
from enum import StrEnum
from functools import cached_property
from typing import cast

from ddev.cli.terminal import Terminal
from ddev.config.constants import AppEnvVars, ConfigEnvVars, VerbosityLevels
from ddev.config.file import ConfigFileWithOverrides, RootConfig
from ddev.repo.core import Repository
from ddev.utils.ci import running_in_ci
from ddev.utils.fs import Path
from ddev.utils.github import GitHubManager
from ddev.utils.platform import Platform


class AnnotationLevel(StrEnum):
    """Severity levels supported by GitHub Actions workflow-command annotations."""

    ERROR = 'error'
    WARNING = 'warning'


class AppLoggingHandler(logging.Handler):
    """Routes Python logging through the Application display methods."""

    def __init__(self, app: Application):
        super().__init__()
        self._app = app

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            self._app.display_error(msg)
        elif record.levelno >= logging.WARNING:
            self._app.display_warning(msg)
        else:
            self._app.display_info(msg)


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

    @cached_property
    def logger(self) -> logging.Logger:
        logger = logging.getLogger("ddev.app")
        if not any(isinstance(h, AppLoggingHandler) for h in logger.handlers):
            logger.addHandler(AppLoggingHandler(self))
            logger.setLevel(logging.WARNING)
        return logger

    @property
    def github(self) -> GitHubManager:
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

        self.__github = GitHubManager(
            self.repo, user=self.config.github.user, token=self.config.github.token, status=self.status
        )

    def abort(self, text='', code=1, **kwargs):
        if text:
            self.display_error(text, **kwargs)
        self.__exit_func(code)

    def annotate_error(self, file: str, message: str, line: int = 1) -> None:
        """Emit a GitHub Actions ``error`` workflow annotation; no-op outside CI."""
        self._emit_github_annotation(AnnotationLevel.ERROR, file, message, line)

    def annotate_warning(self, file: str, message: str, line: int = 1) -> None:
        """Emit a GitHub Actions ``warning`` workflow annotation; no-op outside CI."""
        self._emit_github_annotation(AnnotationLevel.WARNING, file, message, line)

    def annotate_display_queue(
        self, file: str, display_queue: list[tuple[AnnotationLevel, str]], line: int = 1
    ) -> None:
        """Emit one annotation per level from a queue of ``(level, message)`` tuples.

        Messages at the same level are joined with the GitHub Actions newline escape
        (``%0A``) so they render as a single multi-line annotation.
        """
        grouped: defaultdict[AnnotationLevel, list[str]] = defaultdict(list)
        for level, message in display_queue:
            grouped[level].append(message)

        for level in AnnotationLevel:
            if messages := grouped.get(level):
                self._emit_github_annotation(level, file, '%0A'.join(messages), line)

    def _emit_github_annotation(self, level: AnnotationLevel, file: str, message: str, line: int) -> None:
        if not running_in_ci():
            return
        # `print` (not `os.system("echo ...")`): the GH runner parses workflow commands
        # off stdout, and shelling out would corrupt messages containing quotes / `$()`.
        print(f'::{level} file={file},line={line}::{message}')

    # TODO: remove everything below when the old CLI is gone
    def initialize_old_cli(self):
        from copy import deepcopy

        from datadog_checks.dev.tooling.utils import initialize_root

        self.__config.update(deepcopy(self.config.raw_data))
        self.__config['color'] = not self.console.no_color
        self.__config['dd_api_key'] = self.config.orgs.get('default', {}).get('api_key', '')
        self.__config['dd_app_key'] = self.config.orgs.get('default', {}).get('app_key', '')
        # Ensure GitHub config is available for old CLI commands that need it
        self.__config['github'] = {
            'user': self.config.github.user,
            'token': self.config.github.token,
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
