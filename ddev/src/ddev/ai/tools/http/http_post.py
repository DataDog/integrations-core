# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.core.types import ToolResult

from .base import HttpRequestInput, HttpRequestTool


class HttpPostTool(HttpRequestTool):
    """Performs an HTTP POST request with an optional JSON or raw text body to localhost or a literal
    loopback IP address. Use it to verify that a documented local API request shape is accepted.
    Error responses such as 422 are returned with their status and a bounded body excerpt, not
    retried. Responses are returned inline when small, or saved to a run artifact file (always
    when save_response is true) with a JSON result containing the saved_to path and the full body
    when it fits, otherwise a summary. Inspect saved files with grep and read_file. Redirects are not followed."""

    @property
    def name(self) -> str:
        return "http_post"

    async def __call__(self, tool_input: HttpRequestInput) -> ToolResult:
        return await self.execute_request(tool_input, method="POST")
