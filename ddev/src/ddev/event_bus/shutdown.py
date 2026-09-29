# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self


class ShutdownKind(StrEnum):
    """Why a bus was asked to wind down before its work finished."""

    CANCELLED = "cancelled"
    FAILED = "failed"
    TIMED_OUT = "timed out"


@dataclass(frozen=True)
class ShutdownRequest:
    """The shutdown kind and its original error, if any."""

    kind: ShutdownKind
    error: Exception | None = None

    @classmethod
    def cancelled(cls) -> Self:
        return cls(ShutdownKind.CANCELLED)

    @classmethod
    def failed(cls, error: Exception) -> Self:
        return cls(ShutdownKind.FAILED, error)

    @classmethod
    def timed_out(cls, error: Exception) -> Self:
        return cls(ShutdownKind.TIMED_OUT, error)
