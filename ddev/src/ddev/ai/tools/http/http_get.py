# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.ai.tools.core.types import ToolResult

from .base import HttpRequestInput, HttpRequestTool


class HttpGetTool(HttpRequestTool):
    """Performs an HTTP GET request, e.g. to check that an endpoint is reachable or to fetch a
    documented resource from a prepared local API.
    Small responses are returned inline as the status line followed by the body. Large responses,
    or any response when save_response is true, are saved to a run artifact file and a short JSON
    result is returned with the status and saved_to path. The full body is included when it fits;
    otherwise a structural summary is returned. Inspect
    saved files with grep and read_file rather than reading them whole.
    Redirects are not followed."""

    @property
    def name(self) -> str:
        return "http_get"

    async def __call__(self, tool_input: HttpRequestInput) -> ToolResult:
        return await self.execute_request(tool_input, method="GET")
