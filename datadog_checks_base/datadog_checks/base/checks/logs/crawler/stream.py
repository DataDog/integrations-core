# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck


class LogRecord:
    __slots__ = ('cursor', 'data')

    def __init__(self, data: dict[str, str], *, cursor: dict[str, Any] | None):
        self.data = data
        self.cursor = cursor


class LogStream(ABC):
    def __init__(self, *, check: AgentCheck, name: str):
        self.__check = check
        self.__name = name

    @property
    def check(self) -> AgentCheck:
        return self.__check

    @property
    def name(self) -> str:
        return self.__name

    def construct_tags(self, tags: list[str]) -> list[str]:
        formatted_tags = ','.join(tags)
        return f'{self.check.formatted_tags},{formatted_tags}' if self.check.formatted_tags else formatted_tags

    @abstractmethod
    def records(self, *, cursor: dict[str, Any] | None = None) -> Iterable[LogRecord]:
        """
        Yields log records as they are received.
        """
