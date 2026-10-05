# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import ipaddress
import json
from datetime import UTC, datetime
from typing import Annotated, Final, Self

import httpx
from pydantic import AfterValidator, Field, JsonValue, model_validator

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .response_format import MAX_BODY_BYTES, FetchedResponse, format_response
from .response_store import ResponseStore

DEFAULT_TIMEOUT: Final = 10.0
MAX_TIMEOUT: Final = 60.0


class HttpDestinationError(Exception):
    """Raised when a request violates the HTTP tool's destination boundary."""


def requires_http_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return url


def _check_destination(method: str, url: httpx.URL) -> None:
    """Keep POST on the local development host and reject embedded URL credentials."""
    if url.userinfo:
        raise HttpDestinationError("URLs with embedded credentials are not allowed")
    if method != "POST":
        return
    host = url.host.lower()
    if host == "localhost":
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise HttpDestinationError("POST requests require localhost or a literal loopback IP address")


type QueryValue = str | int | float | bool


class HttpRequestInput(BaseToolInput):
    url: Annotated[
        str,
        Field(description="Full URL to request (must start with http:// or https://)"),
        AfterValidator(requires_http_scheme),
    ]
    query: Annotated[
        dict[str, QueryValue | list[QueryValue]] | None,
        Field(description="Query parameters appended to the URL; list values repeat the parameter name."),
    ] = None
    headers: Annotated[
        dict[str, str] | None,
        Field(description="Request headers, including explicit authentication and content negotiation"),
    ] = None
    json_body: Annotated[
        JsonValue,
        Field(
            alias="json",
            description="JSON request body; defaults to Content-Type: application/json. "
            "Omission sends no JSON body; explicit null sends JSON null. Cannot be combined with content.",
        ),
    ] = None
    content: Annotated[
        str | None,
        Field(description="Raw UTF-8 request body; set Content-Type in headers. Cannot be combined with json."),
    ] = None
    timeout: Annotated[
        float,
        Field(
            description=f"Total time budget for the request in seconds (default: {DEFAULT_TIMEOUT:g}, "
            f"max: {MAX_TIMEOUT:g})",
            gt=0,
            le=MAX_TIMEOUT,
        ),
    ] = DEFAULT_TIMEOUT
    save_response: Annotated[
        bool,
        Field(
            description="Save the complete response to a run artifact file even when it is small enough to "
            "return inline. Large responses are saved automatically."
        ),
    ] = False

    @model_validator(mode="after")
    def validate_body(self) -> Self:
        if "json_body" in self.model_fields_set and self.content is not None:
            raise ValueError("Provide either json or content, not both")
        return self


class HttpRequestTool(BaseTool[HttpRequestInput]):
    """Shared transport for the HTTP verb tools.

    Owns bounded streaming, timeouts, and destination checks. Response formatting
    and artifact writing are delegated to `response_format`. Subclasses fix the method in code.
    """

    def __init__(
        self,
        store: ResponseStore | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._store = store
        self._transport = transport

    async def execute_request(self, tool_input: HttpRequestInput, *, method: str) -> ToolResult:
        timeout = tool_input.timeout
        try:
            async with asyncio.timeout(timeout):
                fetched = await self._fetch(tool_input, method=method)
        except HttpDestinationError as e:
            return ToolResult(success=False, error=f"Request blocked: {e}")
        except (TimeoutError, httpx.TimeoutException):
            return ToolResult(success=False, error=f"Request timed out after {timeout}s")
        except httpx.InvalidURL as e:
            return ToolResult(success=False, error=f"Invalid URL {tool_input.url}: {e}")
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"Request failed for {tool_input.url}: {e}")

        if not fetched.complete:
            return ToolResult(
                success=False,
                error=json.dumps(
                    {
                        "status": fetched.status,
                        "content_type": fetched.content_type,
                        "received_bytes": len(fetched.body),
                        "complete": False,
                        "error": f"Response exceeded the {MAX_BODY_BYTES}-byte download limit and was discarded. "
                        "Narrow the request (filters, limit/pagination, a more specific endpoint).",
                    }
                ),
            )
        return format_response(tool_input, method=method, fetched=fetched, store=self._store)

    async def _fetch(self, tool_input: HttpRequestInput, *, method: str) -> FetchedResponse:
        async with httpx.AsyncClient(
            timeout=tool_input.timeout,
            follow_redirects=False,
            # Keep environment proxies and .netrc credentials out of agent requests.
            trust_env=False,
            transport=self._transport,
        ) as client:
            url = httpx.URL(tool_input.url)
            if tool_input.query:
                # `params=` would replace a query already present in the URL instead of merging.
                url = url.copy_merge_params(tool_input.query)
            headers = httpx.Headers(tool_input.headers)
            content = tool_input.content
            if "json_body" in tool_input.model_fields_set and tool_input.json_body is None:
                # httpx treats json=None as no body; an explicitly supplied JSON null is a body.
                content = "null"
                headers.setdefault("Content-Type", "application/json")
            request = client.build_request(method, url, headers=headers, json=tool_input.json_body, content=content)
            _check_destination(method, request.url)
            response = await client.send(request, stream=True)
            try:
                body = bytearray()
                complete = True
                # aiter_bytes yields decompressed content, so the limit bounds memory, not wire size.
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BODY_BYTES:
                        complete = False
                        break
            finally:
                await response.aclose()
        return FetchedResponse(
            url=request.url,
            status=response.status_code,
            content_type=response.headers.get("content-type", ""),
            location=response.headers.get("location"),
            body=bytes(body),
            charset=response.charset_encoding,
            complete=complete,
            fetched_at=datetime.now(UTC),
        )
