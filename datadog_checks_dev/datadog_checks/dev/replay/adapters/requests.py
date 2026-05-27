# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from pathlib import Path
from typing import Any

import pytest
import requests
import urllib3
from requests.structures import CaseInsensitiveDict
from urllib3.response import HTTPResponse

from datadog_checks.dev.replay.redaction import scrub_json, scrub_request_record, scrub_text, scrub_url


class FixtureResponse:
    """Small requests.Response stand-in backed by a fixture body."""

    def __init__(self, record: dict[str, Any]):
        self.status_code = record["status"]
        self.headers = CaseInsensitiveDict(record["headers"])
        self.text = record["body"]
        self.content = self.text.encode("utf-8")
        self.url = record["url"]
        self.reason = "OK"
        self.encoding = "utf-8"

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def __enter__(self) -> "FixtureResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def iter_lines(self, **kwargs: Any) -> list[str]:
        return self.text.split("\n")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self, **kwargs: Any) -> Any:
        return json.loads(self.text, **kwargs)

    def close(self) -> None:
        pass


def _prepared_url(method: str, url: str, kwargs: dict[str, Any] | None = None) -> str:
    params = (kwargs or {}).get('params')
    try:
        prepared = requests.Request(method.upper(), url, params=params).prepare()
        return scrub_url(prepared.url or url)
    except Exception:
        return scrub_url(url)


def _stringify_data(data: Any) -> Any:
    if data is None:
        return None
    if isinstance(data, bytes):
        return scrub_text(data.decode('utf-8', errors='replace'))
    if isinstance(data, str):
        return scrub_text(data)
    return scrub_json(data)


def request_identity(method: str, url: str, kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the scrubbed replay identity for an outbound HTTP request.

    The identity deliberately records request-shaping fields, not response data,
    so replay can distinguish same-URL calls with different verbs or payloads
    without retaining credential material in artifacts.
    """
    kwargs = kwargs or {}
    identity: dict[str, Any] = {
        'method': method.upper(),
        'url': _prepared_url(method, url, kwargs),
    }

    if 'json' in kwargs:
        identity['request_json'] = scrub_json(kwargs.get('json'))
    if 'data' in kwargs:
        identity['request_data'] = _stringify_data(kwargs.get('data'))
    if 'headers' in kwargs and kwargs.get('headers') is not None:
        identity['request_headers'] = scrub_json(dict(kwargs.get('headers') or {}))

    return identity


def build_request_record(
    method: str,
    url: str,
    body: str,
    status: int = 200,
    headers: dict[str, str] | None = None,
    request_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the JSON-serializable fixture shape used by record and replay."""
    return scrub_request_record(
        {
            **request_identity(method, url, request_kwargs),
            "status": status,
            "headers": dict(headers or {"Content-Type": "text/plain"}),
            "body": body,
        }
    )


def build_get_record(url: str, body: str, status: int = 200, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Create a legacy-compatible GET fixture record."""
    return build_request_record('GET', url, body, status=status, headers=headers)


def record_from_response(
    method: str, url: str, response: requests.Response, request_kwargs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a fixture record from a live requests response."""
    return scrub_request_record(
        build_request_record(
            method,
            url,
            response.text,
            status=response.status_code,
            headers=dict(response.headers),
            request_kwargs=request_kwargs,
        )
    )


def record_from_urllib3_response(
    method: str, url: str, response: HTTPResponse, request_kwargs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a fixture record from a live urllib3 response."""
    body = response.data.decode('utf-8', errors='replace')
    return scrub_request_record(
        build_request_record(
            method,
            url,
            body,
            status=response.status,
            headers=dict(response.headers),
            request_kwargs=request_kwargs,
        )
    )


def install_recording_session_request(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, responses_by_request: dict[tuple[str, str], dict[str, Any]]
) -> list[dict[str, Any]]:
    """Record HTTP requests while serving deterministic fixture-backed responses."""
    records: list[dict[str, Any]] = []

    def recorded_request(_session: requests.Session, method: str, url: str, **kwargs: Any) -> FixtureResponse:
        identity = request_identity(method, url, kwargs)
        record = dict(responses_by_request[(identity['method'], identity['url'])])
        records.append(record)
        fixture_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
        return FixtureResponse(record)

    monkeypatch.setattr(requests.Session, "request", recorded_request)
    return records


def install_recording_session_get(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, responses_by_url: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Record HTTP GETs while serving deterministic fixture-backed responses."""
    responses_by_request = {('GET', scrub_url(url)): response for url, response in responses_by_url.items()}
    return install_recording_session_request(monkeypatch, fixture_path, responses_by_request)


def install_live_recording_session_request(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Record real HTTP requests while still returning live responses to the check."""
    records: list[dict[str, Any]] = []
    original_request = requests.Session.request
    original_poolmanager_request = urllib3.PoolManager.request

    def recorded_request(session: requests.Session, method: str, url: str, **kwargs: Any) -> requests.Response:
        response = original_request(session, method, url, **kwargs)
        records.append(record_from_response(method, url, response, request_kwargs=kwargs))
        fixture_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
        return response

    def recorded_poolmanager_request(
        pool_manager: urllib3.PoolManager, method: str, url: str, **kwargs: Any
    ) -> HTTPResponse:
        response = original_poolmanager_request(pool_manager, method, url, **kwargs)
        request_kwargs = dict(kwargs)
        if 'fields' in request_kwargs and 'params' not in request_kwargs:
            request_kwargs['params'] = request_kwargs['fields']
        records.append(record_from_urllib3_response(method, url, response, request_kwargs=request_kwargs))
        fixture_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
        return response

    monkeypatch.setattr(requests.Session, "request", recorded_request)
    monkeypatch.setattr(urllib3.PoolManager, "request", recorded_poolmanager_request)
    return records


def install_live_recording_session_get(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Backward-compatible alias for installing request recording."""
    return install_live_recording_session_request(monkeypatch, fixture_path)


def _assert_record_matches_request(record: dict[str, Any], method: str, url: str, kwargs: dict[str, Any]) -> None:
    identity = request_identity(method, url, kwargs)
    expected_method = record.get('method')
    expected_url = record.get('url')
    if expected_method != identity['method'] or expected_url != identity['url']:
        # Backward compatibility: older GET-only fixtures recorded the raw URL
        # before requests merged `params` into the prepared URL. Accept that
        # legacy identity only when the record has no rich request fields.
        legacy_url = scrub_url(url)
        has_rich_identity = any(field in record for field in ('request_json', 'request_data', 'request_headers'))
        if has_rich_identity or expected_method != identity['method'] or expected_url != legacy_url:
            raise AssertionError(
                'Recorded HTTP request does not match replay request: '
                f"expected {expected_method} {expected_url}, got {identity['method']} {identity['url']}"
            )

    for field in ('request_json', 'request_data'):
        if field in record and record[field] != identity.get(field):
            raise AssertionError(
                f"Recorded HTTP request {field} does not match replay request for "
                f"{identity['method']} {identity['url']}"
            )


def install_replay_session_request(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Replay HTTP requests from recorded fixture records in order."""
    records = json.loads(fixture_path.read_text())
    replayed: list[dict[str, Any]] = []

    def next_record(method: str, url: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        if len(replayed) >= len(records):
            raise AssertionError("No recorded HTTP response available for replay")

        record = records[len(replayed)]
        _assert_record_matches_request(record, method, url, kwargs)
        replayed.append(record)
        return record

    def replayed_request(_session: requests.Session, method: str, url: str, **kwargs: Any) -> FixtureResponse:
        return FixtureResponse(next_record(method, url, kwargs))

    def replayed_poolmanager_request(
        _pool_manager: urllib3.PoolManager, method: str, url: str, **kwargs: Any
    ) -> HTTPResponse:
        request_kwargs = dict(kwargs)
        if 'fields' in request_kwargs and 'params' not in request_kwargs:
            request_kwargs['params'] = request_kwargs['fields']
        record = next_record(method, url, request_kwargs)
        return HTTPResponse(
            body=record['body'].encode('utf-8'),
            status=record['status'],
            headers=record['headers'],
            reason='OK',
            preload_content=True,
        )

    monkeypatch.setattr(requests.Session, "request", replayed_request)
    monkeypatch.setattr(urllib3.PoolManager, "request", replayed_poolmanager_request)
    return replayed


def install_replay_session_get(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Backward-compatible alias for installing request replay."""
    return install_replay_session_request(monkeypatch, fixture_path)
