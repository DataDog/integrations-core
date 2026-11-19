# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path
from typing import Any

from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse
from datadog_checks.control_m import ControlMCheck

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BASE_TAGS = ["control_m_instance:https://example.com/automation-api"]


def _respond(data: Any, status_code: int = 200) -> FakeHTTPResponse:
    if 200 <= status_code < 300:
        body = data if isinstance(data, str) else json.dumps(data)
        return FakeHTTPResponse(status_code=status_code, content=body.encode(), json_result=data)
    return FakeHTTPResponse(status_code=status_code, content=f"Error {status_code}".encode())


def _mock_api(
    check: ControlMCheck,
    fake_http: FakeHTTPClient,
    *,
    servers: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
    jobs_total: int | None = None,
    server_status: int = 200,
    jobs_status: int = 200,
    login_token: str = "test-session-token",
    login_status: int = 200,
    reject_first_server_call: bool = False,
) -> None:
    """Register the Control-M API responses; calling it again replaces them."""
    endpoint = check.instance["control_m_api_endpoint"].rstrip("/")
    servers_url = f"{endpoint}/config/servers"

    if reject_first_server_call:
        fake_http.register_response("GET", servers_url, _respond(None, 401), once=True)
    fake_http.register_response("GET", servers_url, _respond(servers if servers is not None else [], server_status))

    payload: dict[str, Any] = {"statuses": jobs if jobs is not None else []}
    if jobs_total is not None:
        payload["total"] = jobs_total
    # The default `job_status_limit` and `job_name_filter`, URL-encoded into the query string.
    jobs_url = f"{endpoint}/run/jobs/status?limit=10000&jobname=%2A"
    fake_http.register_response("GET", jobs_url, _respond(payload, jobs_status))

    fake_http.register_response("POST", f"{endpoint}/session/login", _respond({"token": login_token}, login_status))


def _load_job(fixture: str, **overrides: Any) -> dict[str, Any]:
    job = json.loads((FIXTURE_DIR / fixture).read_text())
    job.update(overrides)
    return job


def _make_check(instance: dict[str, Any]) -> ControlMCheck:
    return ControlMCheck("control_m", {}, [instance])


def _run_check(check: ControlMCheck) -> None:
    check.check(None)
