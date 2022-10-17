# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from ddev.integration.core import Integration
from ddev.repo.constants import CONFIG_DIRECTORY
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.repo.config import RepositoryConfig


class Repository:
    def __init__(self, name: str, path: str):
        self.__name = name
        self.__path = Path(path)
        self.__integrations = IntegrationRegistry(self)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def integrations(self) -> IntegrationRegistry:
        return self.__integrations

    @cached_property
    def config(self) -> RepositoryConfig:
        from ddev.repo.config import RepositoryConfig

        config_file = self.path / CONFIG_DIRECTORY / 'config.toml'
        if not config_file.is_file():
            return RepositoryConfig({})

        return RepositoryConfig.from_toml_file(config_file)


class IntegrationRegistry:
    def __init__(self, repo: Repository):
        self.__repo = repo
        self.__cache = {}

    @property
    def repo(self) -> Repository:
        return self.__repo

    def get(self, name: str) -> Integration:
        path = self.repo.path / name
        if not path.is_dir():
            raise OSError(f'Integration does not exist: {Path(self.repo.path.name, name)}')
        elif not Integration.is_valid(path):
            raise OSError(f'Path is not an integration nor a Python package: {Path(self.repo.path.name, name)}')

        return Integration(path, self.repo.path, self.repo.config)
