# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Iterable

from ddev.integration.core import Integration
from ddev.repo.constants import CONFIG_DIRECTORY
from ddev.utils.fs import Path
from ddev.utils.git import GitManager

if TYPE_CHECKING:
    from ddev.repo.config import RepositoryConfig


class Repository:
    def __init__(self, name: str, path: str):
        self.__name = name
        self.__path = Path(path).expand()
        self.__git = GitManager(self.__path)
        self.__integrations = IntegrationRegistry(self)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def git(self) -> GitManager:
        return self.__git

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
        if name in self.__cache:
            return self.__cache[name]

        path = self.repo.path / name
        if not path.is_dir():
            raise OSError(f'Integration does not exist: {Path(self.repo.path.name, name)}')

        integration = Integration(path, self.repo.path, self.repo.config)
        if not integration.is_valid:
            raise OSError(f'Path is not an integration nor a Python package: {Path(self.repo.path.name, name)}')

        self.__cache[name] = integration
        return integration

    def iter(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_integration:
                yield integration

    def iter_all(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_valid:
                yield integration

    def iter_packages(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_package:
                yield integration

    def iter_tiles(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_tile:
                yield integration

    def iter_testable(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_testable:
                yield integration

    def iter_shippable(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_shippable:
                yield integration

    def iter_agent_checks(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_agent_check:
                yield integration

    def iter_jmx_checks(self) -> Iterable[Integration]:
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_jmx_check:
                yield integration

    def iter_changed(self) -> Iterable[Integration]:
        changed_root_entries = {relative_path.split('/', 1)[0] for relative_path in self.repo.git.changed_files}
        for path in sorted(self.repo.path.iterdir()):
            integration = self.__get_from_path(path)
            if integration.is_valid and integration.name in changed_root_entries:
                yield integration

    def __get_from_path(self, path: Path) -> Integration:
        if path.name in self.__cache:
            integration = self.__cache[path.name]
        else:
            integration = Integration(path, self.repo.path, self.repo.config)
            self.__cache[path.name] = integration

        return integration
