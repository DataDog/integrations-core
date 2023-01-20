# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from typing import cast

from ddev.cli.terminal import Terminal
from ddev.config.constants import AppEnvVars
from ddev.config.file import ConfigFile, RootConfig
from ddev.repo.core import Repository
from ddev.utils.fs import Path
from ddev.utils.platform import Platform


class Application(Terminal):
    def __init__(self, exit_func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform = Platform(self.display_raw)
        self.__exit_func = exit_func

        self.config_file = ConfigFile()
        self.quiet = self.verbosity < 0
        self.verbose = self.verbosity > 0

        # Lazily set this as we acquire more knowledge about the desired environment
        self.__repo = cast(Repository, None)

        # TODO: remove this when the old CLI is gone
        self.__config = {}

    @property
    def config(self) -> RootConfig:
        return self.config_file.model

    @property
    def repo(self) -> Repository:
        return self.__repo

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

        kwargs = {'here' if self.repo.name == 'local' else self.repo.name: True}
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
