# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import codecs
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Final

import httpx
from pydantic import JsonValue

from ddev.ai.tools.core.truncation import MAX_CHARS
from ddev.ai.tools.core.types import ToolResult

from .response_store import ResponseStore, ResponseStoreError, SavedResponse

if TYPE_CHECKING:
    from .base import HttpRequestInput

# Bodies up to this many characters are returned inline, matching the other tools' output budget.
MAX_INLINE_CHARS: Final = MAX_CHARS
# Largest body held in memory, where JSON can be parsed and pretty-printed before saving.
MAX_BUFFER_BYTES: Final = 4 * 1024 * 1024
# Pretty-printing expands JSON; above this the compact wire text is saved instead.
MAX_FORMATTED_CHARS: Final = 4 * MAX_BUFFER_BYTES
MAX_RECORDED_REQUEST_BODY_CHARS: Final = 2048
MAX_LOCATION_CHARS: Final = 2048

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
    """Metadata shared by every kind of fetched response."""

    url: httpx.URL
    status: int
    content_type: str
    location: str | None
    fetched_at: datetime
    received_bytes: int


@dataclass
class BufferedResponse(HttpResponse):
    """A complete textual response held in memory."""

    body: bytes
    charset: str | None


@dataclass
class StreamedResponse(HttpResponse):
    """A completed textual response streamed to disk without being held in memory."""

    saved: SavedResponse


@dataclass
class UnsupportedResponse(HttpResponse):
    """A response whose content type is not supported; its body was never read."""

    content_length: str | None


def format_response(
    tool_input: HttpRequestInput,
    *,
    method: str,
    fetched: BufferedResponse | StreamedResponse | UnsupportedResponse,
    store: ResponseStore,
) -> ToolResult:
    """Save every textual response and return its body inline when it fits.

    The result starts with a JSON metadata line. When the body has at most `MAX_INLINE_CHARS`
    characters it follows the metadata after a blank line, unescaped; larger bodies are left in
    the saved file for inspection with file tools.
    """
    match fetched:
        case UnsupportedResponse():
            fields = _base_fields(fetched)
            if fetched.content_length is not None:
                fields["content_length"] = fetched.content_length
            fields["note"] = "Unsupported content type; the body was not downloaded or saved."
            return ToolResult(success=True, data=_dump(fields))
        case StreamedResponse():
            fields = _saved_fields(fetched, fetched.saved, representation=stream_representation(fetched.content_type))
            return ToolResult(success=True, data=_render(fields, body=None))
    return _format_buffered_response(tool_input, method=method, fetched=fetched, store=store)


def _format_buffered_response(
    tool_input: HttpRequestInput, *, method: str, fetched: BufferedResponse, store: ResponseStore
) -> ToolResult:
    """Save the buffered body, returning it inline as well when it fits."""
    body_text = _decode(fetched.body, fetched.charset)
    inline = body_text if len(body_text) <= MAX_INLINE_CHARS else None
    representation, saved_text, note = _representation(fetched.content_type, body_text)
    try:
        saved = store.save(
            body=saved_text,
            suffix=".json" if representation == "formatted_json" else ".txt",
            metadata=response_metadata(
                tool_input, method=method, fetched=fetched, representation=representation, note=note
            ),
            stem=method.lower(),
        )
    except ResponseStoreError as e:
        fields = {**_base_fields(fetched), "received_bytes": fetched.received_bytes}
        if inline is None:
            return ToolResult(success=False, error=_dump({**fields, "error": f"Response received but not saved: {e}"}))
        # Saving is a convenience when the body fits; the agent still gets the complete response.
        return ToolResult(success=True, data=_render({**fields, "save_error": str(e)}, body=inline))
    fields = _saved_fields(fetched, saved, representation=representation, note=note)
    return ToolResult(success=True, data=_render(fields, body=inline))


def _saved_fields(
    fetched: HttpResponse, saved: SavedResponse, *, representation: str, note: str | None = None
) -> dict[str, object]:
    """Describe a saved artifact well enough to choose between grep, read_file, and JSON tools."""
    fields: dict[str, object] = {
        **_base_fields(fetched),
        "received_bytes": fetched.received_bytes,
        "lines": saved.lines,
        "representation": representation,
        "saved_to": str(saved.path),
        "metadata_path": str(saved.metadata_path),
    }
    if note:
        fields["note"] = note
    return fields


def _render(fields: dict[str, object], *, body: str | None) -> str:
    fields["body_inline"] = body is not None
    output = _dump(fields)
    # JSON-encoding the body would escape every quote and newline, so it follows the metadata raw.
    return output if body is None else f"{output}\n\n{body}"


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
    fields: dict[str, object] = {"status": fetched.status, "content_type": fetched.content_type}
    if (location := fetched.location) is not None:
        # Bound server-controlled headers so they cannot exhaust the output budget on their own.
        if len(location) > MAX_LOCATION_CHARS:
            location = f"{location[:MAX_LOCATION_CHARS]}… [{len(location) - MAX_LOCATION_CHARS} more characters]"
        fields["redirect_not_followed"] = location
    return fields


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


def stream_representation(content_type: str) -> str:
    """Name a streamed body, which is saved as received without parsing or formatting."""
    return "json" if _is_json(content_type) else "text"


def _decode(body: bytes, charset: str | None) -> str:
    try:
        codecs.lookup(charset or "utf-8")
    except LookupError:
        charset = "utf-8"
    return body.decode(charset or "utf-8", errors="replace")


def _representation(content_type: str, text: str) -> tuple[str, str, str | None]:
    """Prefer formatted JSON when feasible, falling back to the received text.

    Return the representation name, text to save, and any fallback note. `json` means a JSON
    body saved as received, typically on a single line; `text` covers everything else, including
    bodies that claim to be JSON but do not parse.
    """
    if not _is_json(content_type):
        return "text", text, None
    try:
        parsed = json.loads(text)
    except RecursionError:
        return "json", text, "JSON nesting too deep to parse; saved as received"
    except ValueError:
        return "text", text, "Content-Type is JSON but the body is not valid JSON; saved as received text"
    try:
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    except RecursionError:
        return "json", text, "JSON nesting too deep to format; saved as received"
    if len(formatted) > MAX_FORMATTED_CHARS:
        return "json", text, "Formatted JSON exceeded the size limit; saved as received"
    # A formatted representation, not an exact wire-byte capture.
    return "formatted_json", formatted, None


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


def _dump(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)
