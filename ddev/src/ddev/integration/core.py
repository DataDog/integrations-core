# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.repo.config import RepositoryConfig
    from ddev.utils.fs import Path


class Integration:
    def __init__(self, path: Path, repo_path: Path, repo_config: RepositoryConfig):
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

    @cached_property
    def manifest_path(self) -> Path:
        return self.path / 'manifest.json'

    @cached_property
    def __manifest_data(self) -> dict:
        if not self.manifest_path.is_file():
            return {}

        import json

        return json.loads(self.manifest_path.read_text())

    @cached_property
    def manifest(self):
        # TODO: generate a Pydantic model using https://github.com/koxudaxi/datamodel-code-generator
        raise NotImplementedError

    @cached_property
    def display_name(self) -> str:
        if name := self.repo_config.display_name_overrides.get(self.name):
            return name
        else:
            return self.__manifest_data.get('assets', {}).get('integration', {}).get('source_type_name', self.name)

    @classmethod
    def is_valid(cls, path: Path) -> bool:
        return (path / 'manifest.json').is_file() or (path / 'pyproject.toml').is_file()
