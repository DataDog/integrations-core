# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import codecs
import itertools
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Final

import httpx
from pydantic import JsonValue

from ddev.ai.tools.core.types import ToolResult

from .response_store import (
    MAX_ERROR_EXCERPT_CHARS,
    ResponseStore,
    ResponseStoreError,
    SavedResponse,
)

if TYPE_CHECKING:
    from .base import HttpRequestInput

# Upper bound on the text any HTTP tool result returns to the model.
MAX_OUTPUT_CHARS: Final = 4096
MAX_BODY_BYTES: Final = 4 * 1024 * 1024
# Pretty-printing expands JSON; above this the compact wire text is saved instead.
MAX_FORMATTED_CHARS: Final = 4 * MAX_BODY_BYTES
MAX_RECORDED_REQUEST_BODY_CHARS: Final = 2048

SUMMARY_MAX_DEPTH: Final = 2
SUMMARY_MAX_KEYS: Final = 25
SUMMARY_MAX_FIELDS: Final = 10
SUMMARY_MAX_STRING: Final = 80

TEXTUAL_APPLICATION_TYPES: Final = frozenset(
    {
        "application/json",
        "application/xml",
        "application/yaml",
        "application/x-yaml",
        "application/javascript",
        "application/x-javascript",
        "application/openmetrics-text",
        "application/x-www-form-urlencoded",
        "application/graphql",
    }
)
SENSITIVE_NAME_COMPONENTS: Final = frozenset(
    {
        "auth",
        "authorization",
        "authentication",
        "credential",
        "credentials",
        "token",
        "secret",
        "password",
        "passwd",
        "pwd",
        "jwt",
        "key",
        "signature",
        "session",
        "cookie",
        "code",
    }
)

SENSITIVE_NAMES: Final = frozenset(
    {
        "apikey",
        "accesskey",
        "secretkey",
        "privatekey",
        "accesstoken",
        "refreshtoken",
        "authtoken",
        "sessionid",
        "clientsecret",
        "authcode",
        "oauth",
        "oauth2",
        "bearer",
    }
)


@dataclass
class HttpResponse:
    """Metadata shared by buffered responses and responses saved during download."""

    url: httpx.URL
    status: int
    content_type: str
    location: str | None
    fetched_at: datetime
    received_bytes: int


@dataclass
class BufferedResponse(HttpResponse):
    """A response held in memory; incomplete downloads are rejected before formatting."""

    body: bytes
    charset: str | None
    complete: bool


@dataclass
class StreamedResponse(HttpResponse):
    """A completed response streamed to disk, with only a preview retained in memory."""

    saved: SavedResponse
    excerpt: str


def format_response(
    tool_input: HttpRequestInput, *, method: str, fetched: BufferedResponse | StreamedResponse, store: ResponseStore
) -> ToolResult:
    """Return a complete response inline, or save it when requested or too large.

    Saved results include artifact paths and the body when it fits, otherwise a summary.
    Spilled responses already have completed artifacts; their summaries require no body reread.
    Binary bodies are neither returned nor saved.
    """
    if not is_textual(fetched.content_type):
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

    if isinstance(fetched, StreamedResponse):
        return _format_streamed_response(fetched)
    return _format_buffered_response(tool_input, method=method, fetched=fetched, store=store)


def _format_streamed_response(fetched: StreamedResponse) -> ToolResult:
    """Describe completed artifacts using the retained preview, without rereading their body."""
    return _saved_result(
        fetched,
        fetched.saved,
        representation="text",
        summary={"type": "text", "first_line": fetched.excerpt.split("\n", 1)[0][:SUMMARY_MAX_STRING]},
        error_excerpt=fetched.excerpt,
    )


def _format_buffered_response(
    tool_input: HttpRequestInput, *, method: str, fetched: BufferedResponse, store: ResponseStore
) -> ToolResult:
    """Return the buffered body inline, or save it and describe the resulting artifact."""
    body_text = _decode(fetched.body, fetched.charset)
    inline = _inline_output(fetched, body_text)
    fits_inline = len(inline) <= MAX_OUTPUT_CHARS
    if not tool_input.save_response and fits_inline:
        return ToolResult(success=True, data=inline)

    error_excerpt = _excerpt(body_text)
    representation, saved_text, parsed, parse_note = _representation(fetched.content_type, body_text)
    try:
        saved = store.save(
            body=saved_text,
            suffix=".json" if representation == "formatted_json" else ".txt",
            metadata=response_metadata(
                tool_input, method=method, fetched=fetched, representation=representation, note=parse_note
            ),
            stem=method.lower(),
        )
    except ResponseStoreError as e:
        return ToolResult(
            success=False,
            error=_dump(
                {
                    **_base_fields(fetched),
                    "error": f"Response received but not saved: {e}",
                    "excerpt": error_excerpt,
                }
            ),
        )
    return _saved_result(
        fetched,
        saved,
        representation=representation,
        summary=_summarize_json(parsed) if parsed is not None else _summarize_text(saved_text),
        error_excerpt=error_excerpt,
        inline_body=body_text if fits_inline else None,
        note=parse_note,
    )


def _saved_result(
    fetched: HttpResponse,
    saved: SavedResponse,
    *,
    representation: str,
    summary: dict[str, object],
    error_excerpt: str,
    inline_body: str | None = None,
    note: str | None = None,
) -> ToolResult:
    """Build a saved result with the full body if it fits, otherwise its summary and error excerpt."""
    payload: dict[str, object] = {
        **_base_fields(fetched),
        "saved_to": str(saved.path),
        "metadata_path": str(saved.metadata_path),
        "representation": representation,
        "complete": True,
    }
    if note:
        payload["note"] = note
    if inline_body is not None:
        output = _dump({**payload, "body": inline_body})
        if len(output) <= MAX_OUTPUT_CHARS:
            return ToolResult(success=True, data=output)
    if fetched.status >= 400:
        payload["excerpt"] = error_excerpt
    payload["summary"] = summary
    return ToolResult(success=True, data=_fit(payload))


def response_metadata(
    tool_input: HttpRequestInput, *, method: str, fetched: HttpResponse, representation: str, note: str | None = None
) -> dict[str, JsonValue]:
    """Describe the saved response and request, redacting credential-like URL and header fields."""
    metadata: dict[str, JsonValue] = {
        "method": method,
        "url": _safe_url(fetched.url),
        "fetched_at": fetched.fetched_at.isoformat(),
        "status": fetched.status,
        "content_type": fetched.content_type,
        "received_bytes": fetched.received_bytes,
        "representation": representation,
        "complete": True,
    }
    if note:
        metadata["note"] = note
    if "json_body" in tool_input.model_fields_set:
        metadata["request_body"] = _recordable_request_body(tool_input.json_body)
    elif tool_input.content is not None:
        metadata["request_body"] = _recordable_request_body(tool_input.content)
    if tool_input.headers:
        metadata["request_headers"] = {
            name: "REDACTED" if _is_sensitive_name(name) else value for name, value in tool_input.headers.items()
        }

    return metadata


def _base_fields(fetched: HttpResponse) -> dict[str, object]:
    fields: dict[str, object] = {
        "status": fetched.status,
        "content_type": fetched.content_type,
        "received_bytes": fetched.received_bytes,
    }
    if fetched.location is not None:
        # Bound server-controlled headers so they cannot exhaust the output budget on their own.
        fields["redirect_not_followed"] = _excerpt(fetched.location)
    return fields


def _inline_output(fetched: HttpResponse, text: str) -> str:
    header = f"Status: {fetched.status}"
    if fetched.location is not None:
        header = f"{header}\nRedirect not followed: {fetched.location}"
    return f"{header}\n\n{text}"


def is_textual(content_type: str) -> bool:
    """Recognize supported text media types, treating a missing content type as text."""
    media_type = content_type.split(";", 1)[0].strip().lower()
    return (
        not media_type
        or media_type.startswith("text/")
        or media_type in TEXTUAL_APPLICATION_TYPES
        or media_type.endswith(("+json", "+xml"))
    )


def _is_json(content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _decode(body: bytes, charset: str | None) -> str:
    try:
        codecs.lookup(charset or "utf-8")
    except LookupError:
        charset = "utf-8"
    return body.decode(charset or "utf-8", errors="replace")


def _representation(content_type: str, text: str) -> tuple[str, str, JsonValue | None, str | None]:
    """Prefer formatted JSON when feasible, falling back to the received text.

    Return the representation name, text to save, parsed JSON or None, and any fallback note.
    """
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


def _is_sensitive_name(name: str) -> bool:
    """Match recognizable credential names; arbitrary secrets cannot be inferred from names."""
    # Split camelCase and acronym boundaries before separators, without matching inside ordinary words.
    separated = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", separated)
    components = re.split(r"[^a-z0-9]+", separated.lower())
    return any(component in SENSITIVE_NAME_COMPONENTS or component in SENSITIVE_NAMES for component in components)


def _safe_url(url: httpx.URL) -> str:
    """Render `url` for metadata with values of credential-like query parameters redacted."""
    if not url.query:
        return str(url)
    params = [(k, "REDACTED" if _is_sensitive_name(k) else v) for k, v in url.params.multi_items()]
    return str(url.copy_with(params=params))


def _recordable_request_body(json_body: JsonValue) -> JsonValue | str:
    """Keep small request bodies in metadata; replace larger ones with an omission notice."""
    serialized = json.dumps(json_body, ensure_ascii=False)
    if len(serialized) > MAX_RECORDED_REQUEST_BODY_CHARS:
        return f"[omitted: {len(serialized)} characters]"
    return json_body


def _excerpt(text: str) -> str:
    if len(text) <= MAX_ERROR_EXCERPT_CHARS:
        return text
    return f"{text[:MAX_ERROR_EXCERPT_CHARS]}… [{len(text) - MAX_ERROR_EXCERPT_CHARS} more characters]"


def _summarize_json(value: JsonValue, depth: int = SUMMARY_MAX_DEPTH) -> dict[str, object]:
    """Describe JSON structure with limited nesting, keys, fields, and string samples."""
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
    """Shrink summaries and excerpts toward the output budget, retaining response metadata."""
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
