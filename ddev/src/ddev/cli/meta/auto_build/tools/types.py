# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pydantic import BaseModel


class ToolResult(BaseModel):
    """Validated result of a tool call."""

    success: bool
    data: str | None = None
    error: str | None = None
