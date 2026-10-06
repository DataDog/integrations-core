# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from ddev.ai.tools.http.base import HttpRequestInput
from ddev.ai.tools.http.http_get import HttpGetTool
from ddev.ai.tools.http.response_format import BufferedResponse, format_response
from ddev.ai.tools.http.response_store import ResponseStore

from .helpers import parse_result, respond


@pytest.mark.parametrize(
    "content_type,body,representation",
    [
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04binary", None),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK\x03\x04binary", None),
        ("application/graphql", b"query { user { id } }", "text"),
        ("application/yaml", b"user: 1", "text"),
        ("application/x-yaml", b"user: 1", "text"),
        ("application/javascript", b"const user = 1;", "text"),
        ("application/x-javascript", b"const user = 1;", "text"),
        ("application/openmetrics-text", b"requests_total 1", "text"),
        ("application/x-www-form-urlencoded", b"user=1", "text"),
        ("application/xml", b"<user>1</user>", "text"),
        ("application/soap+xml", b"<user>1</user>", "text"),
        ("Application/Problem+JSON; charset=utf-8", b'{"user":1}', "formatted_json"),
        ("application/json", b'{"user":1}', "formatted_json"),
        ("text/plain", b"user: 1", "text"),
        ("", b"user: 1", "text"),
    ],
)
async def test_media_type_controls_response_preservation(
    store: ResponseStore, content_type: str, body: bytes, representation: str | None
):
    response = httpx.Response(200, content=body, headers={"content-type": content_type})

    result = await HttpGetTool(store, transport=respond(response)).run({"url": "http://localhost/api"})

    assert result.success is True
    if representation is None:
        assert "not downloaded" in json.loads(result.data)["note"]
        assert not store.root.exists()
    else:
        fields, inline = parse_result(result.data)
        assert fields["representation"] == representation
        assert inline == body.decode()
        saved = Path(fields["saved_to"]).read_text(encoding="utf-8")
        if representation == "formatted_json":
            assert json.loads(saved) == json.loads(body)
        else:
            assert saved == body.decode()


@pytest.mark.parametrize(
    "name,sensitive",
    [
        (name, True)
        for name in (
            "Authorization",
            "X-API-Key",
            "X-APIKEY",
            "x-apikey",
            "X-ClientSecret",
            "x-clientsecret",
            "apiKey",
            "apikey",
            "access_token",
            "accessToken",
            "JWT",
            "X-Amz-Credential",
            "code",
            "pwd",
            "passwd",
            "clientSecret",
            "session_id",
            "Cookie",
            "password",
            "auth",
            "secret",
            "signature",
            "token",
            "key",
        )
    ]
    + [(name, False) for name in ("keyword", "author", "monkey", "Accept", "Content-Type")],
)
def test_metadata_redacts_credential_names_and_preserves_ordinary_names(tmp_path: Path, name: str, sensitive: bool):
    fetched = BufferedResponse(
        url=httpx.URL("http://localhost/api", params=[(name, "first"), (name, "second")]),
        status=200,
        content_type="text/plain",
        location=None,
        body=b"ok",
        charset=None,
        fetched_at=datetime.now(UTC),
        received_bytes=2,
    )
    result = format_response(
        HttpRequestInput(url=str(fetched.url), headers={name: "header-value"}),
        method="GET",
        fetched=fetched,
        store=ResponseStore(tmp_path),
    )

    metadata = json.loads(Path(parse_result(result.data)[0]["metadata_path"]).read_text(encoding="utf-8"))
    assert httpx.URL(metadata["url"]).params.get_list(name) == (
        ["REDACTED", "REDACTED"] if sensitive else ["first", "second"]
    )
    assert metadata["request_headers"][name] == ("REDACTED" if sensitive else "header-value")
