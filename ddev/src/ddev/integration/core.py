# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import re
from functools import cached_property
from typing import TYPE_CHECKING, Iterator

from ddev.integration.metrics import Metric
from ddev.repo.constants import NOT_SHIPPABLE
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.integration.manifest import Manifest
    from ddev.repo.config import RepositoryConfig


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

    def package_files(self) -> Iterator[Path]:
        for root, _, files in os.walk(self.package_directory):
            for f in files:
                if f.endswith('.py'):
                    yield Path(root, f)

    def requires_changelog_entry(self, path: Path) -> bool:
        return self.package_directory in path.parents or (self.is_package and path == (self.path / 'pyproject.toml'))

    @property
    def release_tag_pattern(self) -> str:
        version_part = r'\d+\.\d+\.\d+'
        if self.name == 'ddev':
            version_part = f'v{version_part}'

        return f'{self.name}-{version_part}'

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
    def normalized_display_name(self) -> str:
        display_name = self.manifest.get('/assets/integration/source_type_name', self.name)
        normalized_integration = re.sub("[^0-9A-Za-z-]", "_", display_name)
        normalized_integration = re.sub("_+", "_", normalized_integration)
        normalized_integration = normalized_integration.strip("_")
        return normalized_integration.lower()

    @cached_property
    def project_file(self) -> Path:
        return self.path / 'pyproject.toml'

    @cached_property
    def metrics_file(self) -> Path:
        relative_path = self.manifest.get('/assets/integration/metrics/metadata_path', 'metadata.csv')
        return self.path / relative_path

    @property
    def metrics(self) -> Iterator[Metric]:
        if not self.metrics_file.exists():
            return

        import csv

        with open(self.metrics_file) as csvfile:
            for row in csv.DictReader(csvfile):
                yield Metric(
                    metric_name=row['metric_name'],
                    metric_type=row['metric_type'],
                    interval=int(row['interval']) if row['interval'] else None,
                    unit_name=row['unit_name'],
                    per_unit_name=row['per_unit_name'],
                    description=row['description'],
                    orientation=int(row['orientation']) if row['orientation'] else None,
                    integration=row['integration'],
                    short_name=row['short_name'],
                    curated_metric=row['curated_metric'],
                )

    @cached_property
    def config_spec(self) -> Path:
        relative_path = self.manifest.get('/assets/integration/configuration/spec', 'assets/configuration/spec.yaml')
        return self.path / relative_path

    @cached_property
    def minimum_base_package_version(self) -> str | None:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name

        from ddev.utils.toml import load_toml_data

        data = load_toml_data(self.project_file.read_text())
        for entry in data['project'].get('dependencies', []):
            dep = Requirement(entry)
            if canonicalize_name(dep.name) == 'datadog-checks-base':
                if dep.specifier:
                    specifier = str(sorted(dep.specifier, key=str)[-1])

                    version_index = 0
                    for i, c in enumerate(specifier):
                        if c.isdigit():
                            version_index = i
                            break

                    return specifier[version_index:]
                else:
                    return None

        return None

    @property
    def project_metadata(self) -> dict:
        import tomli

        with open(self.project_file, 'rb') as f:
            return tomli.load(f)

    @cached_property
    def is_valid(self) -> bool:
        return self.is_integration or self.is_package

    @cached_property
    def is_integration(self) -> bool:
        return (self.path / 'manifest.json').is_file()

    @cached_property
    def has_metrics(self) -> bool:
        return (self.path / 'metadata.csv').is_file()

    @cached_property
    def is_package(self) -> bool:
        return self.project_file.is_file()

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
