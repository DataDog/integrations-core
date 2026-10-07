# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from ddev.ai.tools.http.base import HttpRequestInput
from ddev.ai.tools.http.response_format import (
    BufferedResponse,
    HttpResponse,
    format_response,
    is_textual,
    response_metadata,
)
from ddev.ai.tools.http.response_store import ResponseStore

from .helpers import parse_result


@pytest.mark.parametrize(
    "content_type,supported",
    [
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", False),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", False),
        ("image/png", False),
        ("application/graphql", True),
        ("application/yaml", True),
        ("application/x-yaml", True),
        ("application/javascript", True),
        ("application/x-javascript", True),
        ("application/openmetrics-text", True),
        ("application/x-www-form-urlencoded", True),
        ("application/xml", True),
        ("application/soap+xml", True),
        ("Application/Problem+JSON; charset=utf-8", True),
        ("application/json", True),
        ("text/plain", True),
        ("", True),
    ],
)
def test_media_type_support(content_type: str, supported: bool):
    assert is_textual(content_type) is supported


@pytest.mark.parametrize(
    "content_type,body,representation",
    [
        ("application/json", b'{"user":1}', "formatted_json"),
        ("Application/Problem+JSON; charset=utf-8", b'{"user":1}', "formatted_json"),
        ("application/xml", b"<user>1</user>", "text"),
        ("text/plain", b"user: 1", "text"),
    ],
)
def test_media_type_controls_saved_representation(
    store: ResponseStore, content_type: str, body: bytes, representation: str
):
    fetched = BufferedResponse(
        url=httpx.URL("http://localhost/api"),
        status=200,
        content_type=content_type,
        location=None,
        body=body,
        charset=None,
        fetched_at=datetime.now(UTC),
        received_bytes=len(body),
    )

    result = format_response(HttpRequestInput(url=str(fetched.url)), method="GET", fetched=fetched, store=store)

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


@pytest.mark.parametrize(
    "body_input,recorded",
    [
        (
            {
                "json": {
                    "username": "admin",
                    "password": "login-secret",
                    "profile": {"apiKey": "nested-secret", "name": "Ada"},
                    "items": [{"token": "list-secret", "id": 1}],
                }
            },
            {
                "username": "admin",
                "password": "REDACTED",
                "profile": {"apiKey": "REDACTED", "name": "Ada"},
                "items": [{"token": "REDACTED", "id": 1}],
            },
        ),
        (
            {
                "content": "grant_type=client_credentials&client_secret=form-secret&scope=read",
                "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
            },
            "grant_type=client_credentials&client_secret=REDACTED&scope=read",
        ),
        (
            {
                "content": '{"username": "admin", "password": "raw-secret"}',
                "headers": {"Content-Type": "application/json"},
            },
            '{"username": "admin", "password": "REDACTED"}',
        ),
    ],
)
def test_metadata_redacts_credential_fields_in_request_body(body_input: dict, recorded: object):
    url = "http://localhost/api/login"
    fetched = HttpResponse(
        url=httpx.URL(url),
        status=200,
        content_type="application/json",
        location=None,
        fetched_at=datetime.now(UTC),
        received_bytes=0,
    )

    metadata = response_metadata(
        HttpRequestInput.model_validate({"url": url, **body_input}),
        method="POST",
        fetched=fetched,
        representation="text",
    )

    assert metadata["request_body"] == recorded
