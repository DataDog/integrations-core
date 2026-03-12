# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from pytest import MonkeyPatch
from requests.exceptions import HTTPError

from datadog_checks.control_m import ControlMCheck

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BASE_TAGS = ["control_m_instance:https://example.com/automation-api"]


def _respond(data: Any, status_code: int = 200) -> Mock:
    resp = Mock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    if resp.ok:
        resp.json = Mock(return_value=data)
        resp.text = json.dumps(data) if not isinstance(data, str) else data
        resp.raise_for_status = Mock()
    else:
        resp.text = f"Error {status_code}"
        resp.raise_for_status = Mock(side_effect=HTTPError(f"{status_code} Server Error", response=resp))
    return resp


def _mock_api(
    check: ControlMCheck,
    monkeypatch: MonkeyPatch,
    *,
    servers: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
    jobs_total: int | None = None,
    server_status: int = 200,
    jobs_status: int = 200,
    login_token: str = "test-session-token",
    login_status: int = 200,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "servers": servers if servers is not None else [],
        "jobs": jobs if jobs is not None else [],
        "jobs_total": jobs_total,
    }

    def handle_get(_self: Any, url: str, **kw: Any) -> Mock:
        if "/config/servers" in url:
            return _respond(state["servers"], server_status)
        if "/run/jobs/status" in url:
            payload: dict[str, Any] = {"statuses": state["jobs"]}
            if state["jobs_total"] is not None:
                payload["total"] = state["jobs_total"]
            return _respond(payload, jobs_status)
        return _respond(None, 404)

    def handle_post(_self: Any, url: str, **kw: Any) -> Mock:
        if "/session/login" in url:
            return _respond({"token": login_token}, login_status)
        return _respond(None, 404)

    monkeypatch.setattr(type(check.http), "get", handle_get)
    monkeypatch.setattr(type(check.http), "post", handle_post)
    return state


def _load_job(fixture: str, **overrides: Any) -> dict[str, Any]:
    job = json.loads((FIXTURE_DIR / fixture).read_text())
    job.update(overrides)
    return job


def _make_check(instance: dict[str, Any]) -> ControlMCheck:
    return ControlMCheck("control_m", {}, [instance])


def _run_check(check: ControlMCheck) -> None:
    check.check(None)
