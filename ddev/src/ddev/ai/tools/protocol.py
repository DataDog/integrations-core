# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Protocol

from anthropic.types import ToolParam

from .types import ToolResult


class ToolProtocol[TInput](Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def definition(self) -> ToolParam: ...
    async def run(self, raw: dict[str, object]) -> ToolResult: ...
