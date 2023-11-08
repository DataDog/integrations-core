# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ddev.integration.core import Integration
    from ddev.utils.fs import Path
    from ddev.utils.platform import Platform


class AgentInterface(ABC):
    def __init__(
        self, platform: Platform, integration: Integration, env: str, metadata: dict[str, Any], config_file: Path
    ) -> None:
        self.__platform = platform
        self.__integration = integration
        self.__env = env
        self.__metadata = metadata
        self.__config_file = config_file

    @property
    def platform(self) -> Platform:
        return self.__platform

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
        import re

        if match := re.search(r'^py(\d)\.(\d+)', self.env):
            return int(match.group(1)), int(match.group(2))

        from ddev.repo.constants import PYTHON_VERSION

        major, minor = PYTHON_VERSION.split('.')
        return int(major), int(minor)

    def get_id(self) -> str:
        return f'{self.integration.name}_{self.env}'

    @abstractmethod
    def start(self, *, agent_build: str, local_packages: dict[Path, str], env_vars: dict[str, str]) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def restart(self) -> None:
        ...

    @abstractmethod
    def invoke(self, args: list[str]) -> None:
        ...

    @abstractmethod
    def enter_shell(self) -> None:
        ...
