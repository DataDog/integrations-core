# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ddev.cli.application import Application
    from ddev.integration.core import Integration
    from ddev.utils.fs import Path
    from ddev.utils.platform import Platform


AGENT_IMAGE_REGEX = r'^([^/]+)/([^:]+):(.*)$'
AGENT_VERSION_REGEX = (
    # Main version: 7, 7.69, 7.69.0 ...
    r"^(?P<version>\d+(?:\.[\dx]+)*|latest|main|master|nightly)"
    # rcs: rc.1, rc ...
    r"(?P<rc>-rc(?:\.\d+)?)?"
    # Any suffixes: -jmx, -linux, -full...
    r"(?P<suffixes>(?:-[a-zA-Z0-9]+)*)$"
)


class AgentInterface(ABC):
    build_config_key: str | None = None
    supports_ci = True

    def __init__(
        self, app: Application, integration: Integration, env: str, metadata: dict[str, Any], config_file: Path
    ) -> None:
        self.__app = app
        self.__integration = integration
        self.__env = env
        self.__metadata = metadata
        self.__config_file = config_file

    @property
    def app(self) -> Application:
        return self.__app

    @property
    def platform(self) -> Platform:
        return self.app.platform

    @property
    def integration(self) -> Integration:
        return self.__integration

    @property
    def env(self) -> str:
        return self.__env

    @property
    def metadata(self) -> dict[str, Any]:
        return self.__metadata

    @property
    def config_file(self) -> Path:
        return self.__config_file

    @cached_property
    def python_version(self) -> tuple[int, int]:
        if match := re.search(r'^py(\d)\.(\d+)', self.env):
            return int(match.group(1)), int(match.group(2))

        from ddev.repo.constants import PYTHON_VERSION

        major, minor = PYTHON_VERSION.split('.')
        return int(major), int(minor)

    def normalize_agent_image_name(self, agent_build: str | None) -> str:
        if not agent_build:
            return 'registry.datadoghq.com/agent-dev:master-py3'

        if match := re.match(AGENT_IMAGE_REGEX, agent_build):
            org, image, tag = match.groups()

            if org not in {'datadog', 'registry.datadoghq.com'}:
                # Some non-Datadog image has been selected.
                return agent_build

            version_match = re.match(AGENT_VERSION_REGEX, tag)
            if version_match is None:
                # The tag does not follow a recognized Agent version format.
                return agent_build

            version = version_match.group('version')
            rc = version_match.group('rc') or ''
            suffixes = version_match.group('suffixes')

            # Add a Python suffix when required by a development Agent image.
            if image == 'agent-dev':
                has_python_variant = any(suffix in suffixes for suffix in ('py', 'fips'))
                if not (rc or has_python_variant or version[0].isdigit()):
                    suffixes = f'-py{self.python_version[0]}{suffixes}'

            if self.metadata.get('use_jmx', False) and '-jmx' not in suffixes:
                suffixes += '-jmx'

            return f'{org}/{image}:{version}{rc}{suffixes}'

        return agent_build

    def get_id(self) -> str:
        return f'{self.integration.name}_{self.env}'

    def get_configured_build(self, config: Mapping[str, str]) -> str | None:
        if self.build_config_key is None:
            return None

        return config.get(self.build_config_key)

    @abstractmethod
    def start(self, *, agent_build: str, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def restart(self) -> None: ...

    @abstractmethod
    def invoke(self, args: list[str], *, env_vars: dict[str, str] | None = None) -> None: ...

    @abstractmethod
    def enter_shell(self) -> None: ...

    def sync_config(self) -> None:
        """Synchronize the persisted host configuration with the Agent."""

    def show_logs(self) -> None:
        """Show backend-specific diagnostics for the running Agent."""
        self.invoke(['status'])
