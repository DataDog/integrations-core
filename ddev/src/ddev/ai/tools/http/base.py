# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import codecs
import ipaddress
import itertools
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Final

import httpx
from pydantic import AfterValidator, Field, JsonValue

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.truncation import make_tool_result, truncate
from ddev.ai.tools.core.types import ToolResult

from .response_store import ResponseStore, ResponseStoreError

# Upper bound on the text any HTTP tool result returns to the model.
MAX_OUTPUT_CHARS: Final = 4096
MAX_BODY_BYTES: Final = 4 * 1024 * 1024
# Pretty-printing expands JSON; above this the compact wire text is saved instead.
MAX_FORMATTED_CHARS: Final = 4 * MAX_BODY_BYTES
DEFAULT_TIMEOUT: Final = 10.0
MAX_TIMEOUT: Final = 60.0
MAX_ERROR_EXCERPT_CHARS: Final = 1500
MAX_RECORDED_REQUEST_BODY_CHARS: Final = 2048

SUMMARY_MAX_DEPTH: Final = 2
SUMMARY_MAX_KEYS: Final = 25
SUMMARY_MAX_FIELDS: Final = 10
SUMMARY_MAX_STRING: Final = 80

TEXTUAL_TYPE_MARKERS: Final = ("json", "xml", "yaml", "javascript", "openmetrics-text", "x-www-form-urlencoded")
SENSITIVE_QUERY_MARKERS: Final = ("token", "key", "secret", "password", "auth", "signature", "session")


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
        dict[str, QueryValue] | None,
        Field(description="Query parameters appended to the URL (optional)"),
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


@dataclass
class FetchedResponse:
    url: httpx.URL
    status: int
    content_type: str
    location: str | None
    body: bytes
    charset: str | None
    complete: bool
    fetched_at: datetime


class HttpRequestTool[TInput: HttpRequestInput](BaseTool[TInput]):
    """Shared transport for the HTTP verb tools.

    Owns bounded streaming, timeouts, status/error reporting, response
    summaries, and artifact writing. Subclasses fix the method in code.
    """

    def __init__(
        self,
        store: ResponseStore | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._store = store
        self._transport = transport

    async def execute_request(self, tool_input: TInput, *, method: str, json_body: JsonValue = None) -> ToolResult:
        timeout = tool_input.timeout
        try:
            async with asyncio.timeout(timeout):
                fetched = await self._fetch(tool_input, method=method, json_body=json_body)
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
                error=_dump(
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
        return self._build_result(tool_input, method=method, json_body=json_body, fetched=fetched)

    async def _fetch(self, tool_input: TInput, *, method: str, json_body: JsonValue) -> FetchedResponse:
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
            request = client.build_request(method, url, json=json_body)
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

    def _build_result(
        self, tool_input: TInput, *, method: str, json_body: JsonValue, fetched: FetchedResponse
    ) -> ToolResult:
        if not _is_textual(fetched.content_type):
            return ToolResult(
                success=True,
                data=_dump(
                    {
                        **_base_fields(fetched),
                        "complete": True,
                        "note": "Binary response bodies are not supported; the body was not returned or saved.",
                    }
                ),
            )

        text = _decode(fetched.body, fetched.charset)
        inline = _inline_output(fetched, text)
        store_needed = tool_input.save_response or len(inline) > MAX_OUTPUT_CHARS
        if not store_needed:
            return ToolResult(success=True, data=inline)

        if self._store is None:
            # No artifact storage: return bounded output and say what was omitted.
            result = truncate(inline, max_chars=MAX_OUTPUT_CHARS)
            data = result.output
            if tool_input.save_response:
                data = f"{data}\n\n[save_response ignored: no response storage is configured for this run]"
            return make_tool_result(success=True, data=data, result=result)

        return _save_and_summarize(self._store, method=method, json_body=json_body, fetched=fetched, text=text)


def _save_and_summarize(
    store: ResponseStore, *, method: str, json_body: JsonValue, fetched: FetchedResponse, text: str
) -> ToolResult:
    representation, saved_text, parsed, parse_note = _representation(fetched.content_type, text)
    metadata: dict[str, JsonValue] = {
        "method": method,
        "url": _safe_url(fetched.url),
        "fetched_at": fetched.fetched_at.isoformat(),
        "status": fetched.status,
        "content_type": fetched.content_type,
        "received_bytes": len(fetched.body),
        "representation": representation,
        "complete": True,
    }
    if parse_note:
        metadata["note"] = parse_note
    if json_body is not None:
        metadata["request_body"] = _recordable_request_body(json_body)

    try:
        saved = store.save(
            body=saved_text,
            suffix=".json" if representation == "formatted_json" else ".txt",
            metadata=metadata,
            stem=method.lower(),
        )
    except ResponseStoreError as e:
        return ToolResult(
            success=False,
            error=_dump(
                {
                    **_base_fields(fetched),
                    "error": f"Response received but not saved: {e}",
                    "excerpt": _excerpt(text),
                }
            ),
        )

    payload: dict[str, object] = {
        **_base_fields(fetched),
        "saved_to": str(saved.path),
        "metadata_path": str(saved.metadata_path),
        "representation": representation,
        "complete": True,
    }
    if parse_note:
        payload["note"] = parse_note
    if fetched.status >= 400:
        payload["excerpt"] = _excerpt(text)
    payload["summary"] = _summarize_json(parsed) if parsed is not None else _summarize_text(saved_text)
    return ToolResult(success=True, data=_fit(payload))


def _base_fields(fetched: FetchedResponse) -> dict[str, object]:
    fields: dict[str, object] = {
        "status": fetched.status,
        "content_type": fetched.content_type,
        "received_bytes": len(fetched.body),
    }
    if fetched.location is not None:
        # A server-controlled header; bound it like any other response-derived text so it can't
        # push a result past MAX_OUTPUT_CHARS on its own.
        fields["redirect_not_followed"] = _excerpt(fetched.location)
    return fields


def _inline_output(fetched: FetchedResponse, text: str) -> str:
    header = f"Status: {fetched.status}"
    if fetched.location is not None:
        header = f"{header}\nRedirect not followed: {fetched.location}"
    return f"{header}\n\n{text}"


def _is_textual(content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return not media_type or media_type.startswith("text/") or any(m in media_type for m in TEXTUAL_TYPE_MARKERS)


def _is_json(content_type: str) -> bool:
    return "json" in content_type.split(";", 1)[0].lower()


def _decode(body: bytes, charset: str | None) -> str:
    try:
        codecs.lookup(charset or "utf-8")
    except LookupError:
        charset = "utf-8"
    return body.decode(charset or "utf-8", errors="replace")


def _representation(content_type: str, text: str) -> tuple[str, str, JsonValue | None, str | None]:
    """Return (representation, text to save, parsed JSON or None, note)."""
    if not _is_json(content_type):
        return "text", text, None, None
    try:
        parsed = json.loads(text)
    except RecursionError:
        return "text", text, None, "JSON nesting too deep to parse; saved as received text"
    except ValueError:
        return "text", text, None, "Content-Type is JSON but the body is not valid JSON; saved as received text"
    try:
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    except RecursionError:
        return "text", text, parsed, "JSON nesting too deep to format; saved as received text"
    if len(formatted) > MAX_FORMATTED_CHARS:
        return "text", text, parsed, "Formatted JSON exceeded the size limit; saved as received text"
    # A formatted representation, not an exact wire-byte capture.
    return "formatted_json", formatted, parsed, None


def _safe_url(url: httpx.URL) -> str:
    """Render `url` for metadata with values of credential-like query parameters redacted."""
    if not url.query:
        return str(url)
    params = [
        (k, "REDACTED" if any(m in k.lower() for m in SENSITIVE_QUERY_MARKERS) else v)
        for k, v in url.params.multi_items()
    ]
    return str(url.copy_with(params=params))


def _recordable_request_body(json_body: JsonValue) -> JsonValue | str:
    serialized = json.dumps(json_body, ensure_ascii=False)
    if len(serialized) > MAX_RECORDED_REQUEST_BODY_CHARS:
        return f"[omitted: {len(serialized)} characters]"
    return json_body


def _excerpt(text: str) -> str:
    if len(text) <= MAX_ERROR_EXCERPT_CHARS:
        return text
    return f"{text[:MAX_ERROR_EXCERPT_CHARS]}… [{len(text) - MAX_ERROR_EXCERPT_CHARS} more characters]"


def _summarize_json(value: JsonValue, depth: int = SUMMARY_MAX_DEPTH) -> dict[str, object]:
    match value:
        case dict():
            summary: dict[str, object] = {"type": "object", "keys": list(value)[:SUMMARY_MAX_KEYS]}
            if len(value) > SUMMARY_MAX_KEYS:
                summary["key_count"] = len(value)
            if depth > 1:
                summary["fields"] = {
                    k: _summarize_json(v, depth - 1) for k, v in itertools.islice(value.items(), SUMMARY_MAX_FIELDS)
                }
            return summary
        case list():
            summary = {"type": "array", "length": len(value)}
            if value and depth > 1:
                summary["first_item"] = _summarize_json(value[0], depth - 1)
            return summary
        case str():
            return {"type": "string", "length": len(value), "sample": value[:SUMMARY_MAX_STRING]}
        case bool():
            return {"type": "boolean", "value": value}
        case None:
            return {"type": "null"}
        case _:
            return {"type": "number", "value": value}


def _summarize_text(text: str) -> dict[str, object]:
    first_line = text.split("\n", 1)[0]
    return {"type": "text", "lines": text.count("\n") + 1, "first_line": first_line[:SUMMARY_MAX_STRING]}


def _dump(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _fit(payload: dict[str, object]) -> str:
    """Serialize `payload` within MAX_OUTPUT_CHARS, shedding the summary before anything else."""
    output = _dump(payload)
    if len(output) <= MAX_OUTPUT_CHARS:
        return output
    summary = payload.get("summary")
    if isinstance(summary, dict) and "fields" in summary:
        payload["summary"] = {k: v for k, v in summary.items() if k != "fields"}
        output = _dump(payload)
    if len(output) > MAX_OUTPUT_CHARS:
        payload["summary"] = {"omitted": "summary too large; inspect the saved file with grep/read_file"}
        output = _dump(payload)
    if len(output) > MAX_OUTPUT_CHARS and "excerpt" in payload:
        payload["excerpt"] = _excerpt(str(payload["excerpt"]))[:500]
        output = _dump(payload)
    return output
