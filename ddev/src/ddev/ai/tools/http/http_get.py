# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.core.types import ToolResult

from .base import HttpRequestInput, HttpRequestTool


class HttpGetTool(HttpRequestTool):
    """Performs an HTTP GET request, e.g. to check that an endpoint is reachable or to fetch a
    documented resource from a prepared local API.
    Every text response is saved to a run artifact file. The result starts with a JSON metadata line
    (status, content_type, received_bytes, lines, representation, saved_to, body_inline). When the
    body has at most 50,000 characters it follows after a blank line; otherwise inspect saved_to with
    grep and read_file (lines tells you whether line-based paging will help; formatted_json files are
    pretty-printed). Unsupported (binary) content types are reported without downloading the body.
    Redirects are not followed."""

    @property
    def name(self) -> str:
        return "http_get"

    async def __call__(self, tool_input: HttpRequestInput) -> ToolResult:
        return await self.execute_request(tool_input, method="GET")
