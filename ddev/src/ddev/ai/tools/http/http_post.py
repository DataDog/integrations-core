# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field, JsonValue

from ddev.ai.tools.core.types import ToolResult

from .base import HttpRequestInput, HttpRequestTool


class HttpPostInput(HttpRequestInput):
    json_body: Annotated[
        JsonValue,
        Field(alias="json", description="JSON request body (optional). Sent with Content-Type: application/json."),
    ] = None


class HttpPostTool(HttpRequestTool[HttpPostInput]):
    """Performs an HTTP POST request with an optional JSON body to localhost or a literal
    loopback IP address. Use it to verify that a documented local API request shape is accepted.
    Error responses such as 422 are returned with their status and a bounded body excerpt, not
    retried. Responses are returned inline when small, or saved to a run artifact file (always
    when save_response is true) with a short JSON result containing the saved_to path. Inspect
    saved files with grep and read_file. Redirects are not followed."""

    @property
    def name(self) -> str:
        return "http_post"

    async def __call__(self, tool_input: HttpPostInput) -> ToolResult:
        return await self.execute_request(tool_input, method="POST", json_body=tool_input.json_body)
