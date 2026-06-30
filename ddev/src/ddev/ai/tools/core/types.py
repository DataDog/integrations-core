# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pydantic import BaseModel, Field

from ddev.ai.accounting.tokens import Tokens


class ToolResult(BaseModel):
    """Validated result of a tool call."""

    success: bool
    data: str | None = None
    error: str | None = None
    truncated: bool = False
    total_size: int | None = None
    shown_size: int | None = None
    hint: str | None = None
    tokens: Tokens = Field(default_factory=Tokens)
