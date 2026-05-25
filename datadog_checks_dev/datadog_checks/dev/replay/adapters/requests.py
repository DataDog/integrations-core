# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from pathlib import Path
from typing import Any

import pytest
import requests


class FixtureResponse:
    """Small requests.Response stand-in backed by a fixture body."""

    def __init__(self, record: dict[str, Any]):
        self.status_code = record["status"]
        self.headers = dict(record["headers"])
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


def build_get_record(url: str, body: str, status: int = 200, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Create the JSON-serializable fixture shape used by record and replay."""
    return {
        "method": "GET",
        "url": url,
        "status": status,
        "headers": dict(headers or {"Content-Type": "text/plain"}),
        "body": body,
    }


def record_from_response(url: str, response: requests.Response) -> dict[str, Any]:
    """Create a fixture record from a live requests response."""
    return build_get_record(url, response.text, status=response.status_code, headers=dict(response.headers))


def install_recording_session_get(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, responses_by_url: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Record HTTP GETs while serving deterministic fixture-backed responses."""
    records: list[dict[str, Any]] = []

    def recorded_get(_session: requests.Session, url: str, **kwargs: Any) -> FixtureResponse:
        record = dict(responses_by_url[url])
        records.append(record)
        fixture_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
        return FixtureResponse(record)

    monkeypatch.setattr(requests.Session, "get", recorded_get)
    return records


def install_live_recording_session_get(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Record real HTTP GETs while still returning live responses to the check."""
    records: list[dict[str, Any]] = []
    original_get = requests.Session.get

    def recorded_get(session: requests.Session, url: str, **kwargs: Any) -> requests.Response:
        response = original_get(session, url, **kwargs)
        records.append(record_from_response(url, response))
        fixture_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
        return response

    monkeypatch.setattr(requests.Session, "get", recorded_get)
    return records


def install_replay_session_get(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Replay HTTP GETs from recorded fixture records in order."""
    records = json.loads(fixture_path.read_text())
    replayed: list[dict[str, Any]] = []

    def replayed_get(_session: requests.Session, url: str, **kwargs: Any) -> FixtureResponse:
        if len(replayed) >= len(records):
            raise AssertionError("No recorded HTTP response available for replay")

        record = records[len(replayed)]
        if record["method"] != "GET" or record["url"] != url:
            raise AssertionError("Recorded HTTP request does not match replay request")

        replayed.append(record)
        return FixtureResponse(record)

    monkeypatch.setattr(requests.Session, "get", replayed_get)
    return replayed
