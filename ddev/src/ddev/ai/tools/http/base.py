# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import ipaddress
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Final, Self

import httpx
from pydantic import AfterValidator, Field, JsonValue, model_validator

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult

from .response_format import (
    MAX_BUFFER_BYTES,
    BufferedResponse,
    StreamedResponse,
    UnsupportedResponse,
    format_response,
    is_textual,
    response_metadata,
    stream_representation,
)
from .response_store import ResponseStore, ResponseStoreError

DEFAULT_TIMEOUT: Final = 10.0
MAX_TIMEOUT: Final = 60.0

# Engineering default for the decoded-download ceiling, independent of the buffering threshold.
MAX_DOWNLOAD_BYTES: Final = 1024 * 1024 * 1024
STREAM_CHUNK_BYTES: Final = 64 * 1024


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
        store: ResponseStore,
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
        except ResponseStoreError as e:
            return ToolResult(success=False, error=f"Response could not be saved: {e}")
        except HttpDestinationError as e:
            return ToolResult(success=False, error=f"Request blocked: {e}")
        except (TimeoutError, httpx.TimeoutException):
            return ToolResult(success=False, error=f"Request timed out after {timeout}s")
        except httpx.InvalidURL as e:
            return ToolResult(success=False, error=f"Invalid URL {tool_input.url}: {e}")
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"Request failed for {tool_input.url}: {e}")

        return format_response(tool_input, method=method, fetched=fetched, store=self._store)

    async def _fetch(
        self, tool_input: HttpRequestInput, *, method: str
    ) -> BufferedResponse | StreamedResponse | UnsupportedResponse:
        """Download once, buffering text up to 4 MiB and streaming larger bodies to disk.

        Unsupported content types are recognized from the headers and their body is never read.
        Text responses up to 4 MiB return as `BufferedResponse` for `format_response` to save.
        Above 4 MiB, save the buffered prefix and remaining chunks as text, up to 1 GiB;
        exceeding that download cap raises an error and removes the partial file.
        """
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
                content_type = response.headers.get("content-type", "")
                if not is_textual(content_type):
                    return UnsupportedResponse(
                        url=request.url,
                        status=response.status_code,
                        content_type=content_type,
                        location=response.headers.get("location"),
                        fetched_at=datetime.now(UTC),
                        received_bytes=0,
                        content_length=response.headers.get("content-length"),
                    )
                fetched = BufferedResponse(
                    url=request.url,
                    status=response.status_code,
                    content_type=content_type,
                    location=response.headers.get("location"),
                    body=b"",
                    charset=response.charset_encoding,
                    fetched_at=datetime.now(UTC),
                    received_bytes=0,
                )
                body = bytearray()
                chunks = response.aiter_bytes(chunk_size=STREAM_CHUNK_BYTES)
                async for chunk in chunks:
                    fetched.received_bytes += len(chunk)
                    if fetched.received_bytes > MAX_BUFFER_BYTES:
                        saved, received_bytes = await self._store.save_stream(
                            chunks=_with_prefix(body, chunk, chunks),
                            charset=fetched.charset,
                            metadata=response_metadata(
                                tool_input,
                                method=method,
                                fetched=fetched,
                                representation=stream_representation(content_type),
                                note="Streamed response saved as received text without JSON parsing or formatting",
                            ),
                            stem=method.lower(),
                            max_bytes=MAX_DOWNLOAD_BYTES,
                        )
                        return StreamedResponse(
                            url=fetched.url,
                            status=fetched.status,
                            content_type=fetched.content_type,
                            location=fetched.location,
                            fetched_at=fetched.fetched_at,
                            received_bytes=received_bytes,
                            saved=saved,
                        )
                    body.extend(chunk)
                fetched.body = bytes(body)
                return fetched
            finally:
                await response.aclose()


async def _with_prefix(prefix: bytearray, first_chunk: bytes, chunks: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    # Flush retained bytes in small pieces; HTTPX's upstream decompression buffers are independent.
    for offset in range(0, len(prefix), STREAM_CHUNK_BYTES):
        yield bytes(prefix[offset : offset + STREAM_CHUNK_BYTES])
    prefix.clear()
    yield first_chunk
    async for chunk in chunks:
        yield chunk
