# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.config.registry import ResourceKind


class ConfigError(Exception):
    """Wraps Pydantic ValidationError or YAML errors with a user-friendly message."""


class ErrorKind(StrEnum):
    """The category of a flow validation error.

    The first six members mirror the ``ResourceKind`` values (a reference error is
    categorized by the kind of the referenced resource); ``DEPENDENCY`` and ``VARIABLE``
    are structural problems not tied to a single resource.
    """

    FLOW = auto()
    PHASE = auto()
    AGENT = auto()
    PROMPT = auto()
    GOAL = auto()
    MEMORY_PROMPT = auto()
    DEPENDENCY = auto()
    VARIABLE = auto()

    @classmethod
    def for_resource(cls, kind: ResourceKind) -> ErrorKind:
        """The error category for a problem with a resource of the given kind."""
        return cls(kind)


@dataclass(frozen=True)
class FlowError:
    kind: ErrorKind
    message: str
    subject: str | None = None  # the named entity the error is about (phase/agent/ref/variable name)
    phase: str | None = None  # the phase context, when the error occurs inside one
    sources: list[Path] = field(default_factory=list)  # every file relevant to fixing it
