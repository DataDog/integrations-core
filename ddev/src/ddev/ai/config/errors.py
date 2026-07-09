# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.config.models import ResolvedFlow


class FlowConfigError(Exception):
    """Wraps Pydantic ValidationError or YAML errors with a user-friendly message."""


class ConfigStatus(StrEnum):
    OK = "ok"
    BROKEN = "broken"


class ErrorKind(StrEnum):
    FLOW = "flow"
    PHASE = "phase"
    AGENT = "agent"
    PROMPT = "prompt"
    GOAL = "goal"
    MEMORY_PROMPT = "memory_prompt"
    DEPENDENCY = "dependency"
    VARIABLE = "variable"


@dataclass(frozen=True)
class FlowError:
    kind: ErrorKind
    message: str
    subject: str | None = None  # the named entity the error is about (phase/agent/ref/variable name)
    phase: str | None = None  # the phase context, when the error occurs inside one
    sources: list[Path] = field(default_factory=list)  # every file relevant to fixing it


@dataclass
class FlowDiagnostics:
    name: str
    status: ConfigStatus
    errors: list[FlowError]
    resolved: ResolvedFlow | None = None
