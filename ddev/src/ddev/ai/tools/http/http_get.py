# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from typing import Annotated

import httpx

from ddev.ai.tools.core.base import BaseTool
from ddev.ai.tools.core.truncation import TruncateResult, truncate
from ddev.ai.tools.core.types import ToolResult


@dataclass
class HttpGetInput:
    url: Annotated[str, "Full URL to probe (must start with http:// or https://)"]
    timeout: Annotated[float, "Request timeout in seconds (default: 10)"] = 10.0


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

        if not url.startswith(("http://", "https://")):
            return ToolResult(success=False, error="URL must start with http:// or https://")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
        except httpx.TimeoutException:
            return ToolResult(success=False, error=f"Request timed out after {timeout}s")
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"Request failed: {e}")

        body = response.text
        result: TruncateResult = truncate(body)

        status_line = f"Status: {response.status_code}"
        output = f"{status_line}\n\n{result.output}"

        if result.truncated and result.meta is not None:
            return ToolResult(
                success=response.is_success,
                data=output,
                truncated=True,
                total_size=result.meta.total_size,
                shown_size=result.meta.shown_size,
                hint=result.meta.hint,
            )

        return ToolResult(success=response.is_success, data=output)
