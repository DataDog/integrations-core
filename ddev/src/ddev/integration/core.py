# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from ddev.repo.constants import NOT_SHIPPABLE

if TYPE_CHECKING:
    from ddev.integration.manifest import Manifest
    from ddev.repo.config import RepositoryConfig
    from ddev.utils.fs import Path


class Integration:
    def __init__(self, path: Path, repo_path: Path, repo_config: RepositoryConfig):
        # Do nothing but simple assignment here as we initialize often without
        # use just to access the `is_*` properties
        self.__path = path
        self.__name = path.name
        self.__repo_path = repo_path
        self.__repo_config = repo_config

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def name(self) -> str:
        return self.__name

    @property
    def repo_path(self) -> Path:
        return self.__repo_path

    @property
    def repo_config(self) -> RepositoryConfig:
        return self.__repo_config

    @property
    def package_directory_name(self) -> str:
        return self.name.replace('-', '_')

    @cached_property
    def package_directory(self) -> Path:
        if self.name == 'ddev':
            return self.path / 'src' / 'ddev'
        else:
            if self.name == 'datadog_checks_base':
                directory = 'base'
            elif self.name == 'datadog_checks_dev':
                directory = 'dev'
            elif self.name == 'datadog_checks_downloader':
                directory = 'downloader'
            else:
                directory = self.package_directory_name

            return self.path / 'datadog_checks' / directory

    @cached_property
    def manifest(self) -> Manifest:
        from ddev.integration.manifest import Manifest

        return Manifest(self.path / 'manifest.json')

    @cached_property
    def display_name(self) -> str:
        if name := self.repo_config.get(f'/overrides/display-name/{self.name}', None):
            return name
        else:
            return self.manifest.get('/assets/integration/source_type_name', self.name)

    @cached_property
    def is_valid(self) -> bool:
        return self.is_integration or self.is_package

    @cached_property
    def is_integration(self) -> bool:
        return (self.path / 'manifest.json').is_file()

    @cached_property
    def is_package(self) -> bool:
        return (self.path / 'pyproject.toml').is_file()

    @cached_property
    def is_tile(self) -> bool:
        return self.is_integration and not self.is_package

    @cached_property
    def is_testable(self) -> bool:
        # TODO: remove tox when the Hatch migration is complete
        return (self.path / 'hatch.toml').is_file() or (self.path / 'tox.ini').is_file()

    @cached_property
    def is_shippable(self) -> bool:
        return self.is_package and self.path.name not in NOT_SHIPPABLE

    @cached_property
    def is_agent_check(self) -> bool:
        package_root = self.path / 'datadog_checks' / self.package_directory_name / '__init__.py'
        if not package_root.is_file():
            return False

        contents = package_root.read_text()

        # Anything more than the version must be a subclass of the base class
        return contents.count('import ') > 1

    @cached_property
    def is_jmx_check(self) -> bool:
        return (self.path / 'datadog_checks' / self.package_directory_name / 'data' / 'metrics.yaml').is_file()

    def __eq__(self, other):
        return other.path == self.path
