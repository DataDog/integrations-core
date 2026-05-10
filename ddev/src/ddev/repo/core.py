# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from functools import cached_property
from typing import TYPE_CHECKING, Dict, Iterable

from ddev.integration.core import Integration
from ddev.repo.constants import CONFIG_DIRECTORY, DEFAULT_ORG, FULL_NAMES
from ddev.utils.fs import Path
from ddev.utils.git import GitRepository

if TYPE_CHECKING:
    from ddev.repo.config import RepositoryConfig


_GIT_REMOTE_PATTERNS = (
    # SSH form: git@github.com:Org/repo(.git)?
    re.compile(r'^(?:[^@]+@)?[^:/]+:(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$'),
    # HTTP(S) / git:// form: scheme://[user[:pass]@]host[:port]/Org/repo(.git)?
    re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*://[^/]+/(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$'),
)


def parse_remote_url(url: str) -> tuple[str, str] | None:
    """Parse a git remote URL into `(org, repo)`. Returns None if the URL form is unrecognised."""
    for pattern in _GIT_REMOTE_PATTERNS:
        match = pattern.match(url)
        if match:
            return match.group('org'), match.group('repo')
    return None


def _read_origin_url_from_git_config(repo_path: Path) -> str | None:
    """Read the `origin` remote URL from `.git/config`, following worktree pointers if needed.

    Implemented as file IO (no subprocess) so it is invisible to test mocks that intercept
    `subprocess.run` or `GitRepository.capture`.
    """
    import configparser

    git_dir = repo_path / '.git'
    try:
        if git_dir.is_file():
            content = git_dir.read_text()
            for line in content.splitlines():
                if line.startswith('gitdir:'):
                    pointer = line.split(':', 1)[1].strip()
                    git_dir = Path(pointer)
                    if not git_dir.is_absolute():
                        git_dir = (repo_path / git_dir).resolve()
                    break
            else:
                return None
        config_path = git_dir / 'config'
        if not config_path.is_file():
            common_pointer = git_dir / 'commondir'
            if common_pointer.is_file():
                common = common_pointer.read_text().strip()
                common_dir = Path(common)
                if not common_dir.is_absolute():
                    common_dir = (git_dir / common_dir).resolve()
                config_path = common_dir / 'config'
        if not config_path.is_file():
            return None
        parser = configparser.ConfigParser(strict=False)
        parser.read(config_path, encoding='utf-8')
        section = 'remote "origin"'
        if parser.has_option(section, 'url'):
            return parser.get(section, 'url').strip() or None
    except (OSError, configparser.Error):
        return None
    return None


class Repository:
    def __init__(self, name: str, path: str):
        self.__name = name
        self.__path = Path(path).expand()
        self.__git = GitRepository(self.__path)
        self.__org, self.__full_name = self.__derive_identity()
        self.__integrations = IntegrationRegistry(self)

    def __derive_identity(self) -> tuple[str, str]:
        remote_url = _read_origin_url_from_git_config(self.__path)
        if remote_url:
            parsed = parse_remote_url(remote_url)
            if parsed is not None:
                return parsed
        return DEFAULT_ORG, FULL_NAMES.get(self.__name, self.__name)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def org(self) -> str:
        return self.__org

    @property
    def full_name(self) -> str:
        return self.__full_name

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def git(self) -> GitRepository:
        return self.__git

    @property
    def integrations(self) -> IntegrationRegistry:
        return self.__integrations

    @cached_property
    def config(self) -> RepositoryConfig:
        from ddev.repo.config import RepositoryConfig

        return RepositoryConfig(self.path / CONFIG_DIRECTORY / 'config.toml')

    @cached_property
    def agent_requirements(self) -> Path:
        return self.path / 'agent_requirements.in'

    @cached_property
    def agent_release_requirements(self) -> Path:
        return self.path / 'requirements-agent-release.txt'

    @cached_property
    def agent_changelog(self) -> Path:
        return self.path / 'AGENT_CHANGELOG.md'

    @cached_property
    def agent_integrations_file(self) -> Path:
        return self.path / 'AGENT_INTEGRATIONS.md'


class IntegrationRegistry:
    def __init__(self, repo: Repository):
        self.__repo = repo
        self.__cache: Dict[str, Integration] = {}

    @property
    def repo(self) -> Repository:
        return self.__repo

    def get(self, name: str) -> Integration:
        if name in self.__cache:
            return self.__cache[name]

        path = self.repo.path / name
        if not path.is_dir() or self.repo.git.is_worktree(path):
            raise OSError(f'Integration does not exist: {Path(self.repo.path.name, name)}')

        integration = Integration(path, self.repo.path, self.repo.config)
        if not integration.is_valid:
            raise OSError(f'Path is not an integration nor a Python package: {Path(self.repo.path.name, name)}')

        self.__cache[name] = integration
        return integration

    def iter(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all integrations.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_integration:
                yield integration

    def iter_all(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all targets i.e. any integration or Python package.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_valid:
                yield integration

    def iter_packages(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all Python packages.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_package:
                yield integration

    def iter_tiles(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all tile-only integrations.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_tile:
                yield integration

    def iter_testable(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all targets that can be tested.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_testable:
                yield integration

    def iter_shippable(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all integrations that can be shipped by the Agent.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_shippable:
                yield integration

    def iter_agent_checks(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all Python checks.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_agent_check:
                yield integration

    def iter_jmx_checks(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all JMX checks.
        """
        for integration in self.__iter_filtered(selection):
            if integration.is_jmx_check:
                yield integration

    def iter_changed(self) -> Iterable[Integration]:
        """
        Iterate over all integrations that have changed.
        """
        yield from self.iter_all()

    def iter_changed_code(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        """
        Iterate over all integrations that have changes that could affect built distributions.
        """
        for integration in self.__iter_filtered(selection):
            for relative_path in self.repo.git.changed_files():
                if integration.requires_changelog_entry(self.repo.path / relative_path):
                    yield integration
                    break

    def __iter_filtered(self, selection: Iterable[str] = ()) -> Iterable[Integration]:
        selected = self.__finalize_selection(selection)
        if selected is None:
            return

        for path in sorted(self.repo.path.iterdir()):
            # Ignore any non-directory entries since integrations are always directories
            # Hidden directories are also not integrations
            if not path.is_dir() or path.name.startswith('.'):
                continue

            # Ignore any subdirectory that is a worktree
            if self.repo.git.is_worktree(path):
                continue

            integration = self.__get_from_path(path)

            if selected and integration.name not in selected:
                continue

            yield integration

    def __get_from_path(self, path: Path) -> Integration:
        if path.name in self.__cache:
            integration = self.__cache[path.name]
        else:
            integration = Integration(path, self.repo.path, self.repo.config)
            self.__cache[path.name] = integration

        return integration

    def __finalize_selection(self, selection: Iterable[str]) -> set[str] | None:
        if not selection or 'changed' in selection:
            return self.__get_changed_root_entries() or None

        return set() if 'all' in selection else set(selection)

    def __get_changed_root_entries(self) -> set[str]:
        return {relative_path.split('/', 1)[0] for relative_path in self.repo.git.changed_files()}
