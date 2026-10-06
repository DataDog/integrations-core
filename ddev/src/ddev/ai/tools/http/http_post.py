# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.core.types import ToolResult

from .base import HttpRequestInput, HttpRequestTool


class HttpPostTool(HttpRequestTool):
    """Performs an HTTP POST request with an optional JSON or raw text body to localhost or a literal
    loopback IP address. Use it to verify that a documented local API request shape is accepted.
    Error responses such as 422 are returned with their status and body, not retried.
    Every text response is saved to a run artifact file. The result starts with a JSON metadata line
    (status, content_type, received_bytes, lines, representation, saved_to, body_inline). When the
    body has at most 50,000 characters it follows after a blank line; otherwise inspect saved_to with
    grep and read_file. Redirects are not followed."""

    @property
    def name(self) -> str:
        return "http_post"

    async def __call__(self, tool_input: HttpRequestInput) -> ToolResult:
        return await self.execute_request(tool_input, method="POST")
