# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Tokens(BaseModel):
    """Accumulable input/output/cache token totals."""

    model_config = ConfigDict(frozen=True)

    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_creation: int = 0

    def __add__(self, other: Tokens) -> Tokens:
        return Tokens(
            input=self.input + other.input,
            output=self.output + other.output,
            cache_read=self.cache_read + other.cache_read,
            cache_creation=self.cache_creation + other.cache_creation,
        )

    def __radd__(self, other: Tokens | int) -> Tokens:
        if other == 0:
            return self
        return NotImplemented
