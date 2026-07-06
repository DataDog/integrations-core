# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

import httpx
from pydantic import Field, field_validator

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.truncation import make_tool_result, truncate
from ddev.ai.tools.core.types import ToolResult


class HttpGetInput(BaseToolInput):
    url: Annotated[str, Field(description="Full URL to probe (must start with http:// or https://)")]
    timeout: Annotated[float, Field(description="Request timeout in seconds (default: 10)", gt=0)] = 10.0

    @field_validator("url")
    @classmethod
    def url_must_have_http_scheme(cls, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return url


class HttpGetTool(BaseTool[HttpGetInput]):
    """Performs an HTTP GET request to check if an endpoint is reachable.
    Use to validate that a metrics endpoint is accessible and inspect its response.
    Returns the HTTP status code and response body (truncated if large)."""

    @property
    def name(self) -> str:
        return "http_get"

    async def __call__(self, tool_input: HttpGetInput) -> ToolResult:
        url: str = tool_input.url
        timeout: float = tool_input.timeout

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
        except httpx.TimeoutException:
            return ToolResult(success=False, error=f"Request timed out after {timeout}s")
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"Request failed for {url}: {e}")

        body = response.text
        result = truncate(body)

        status_line = f"Status: {response.status_code}"
        output = f"{status_line}\n\n{result.output}"

        return make_tool_result(success=True, data=output, result=result)
