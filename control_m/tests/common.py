# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.control_m import ControlMCheck

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BASE_TAGS = ["control_m_instance:https://example.com/automation-api"]


def _respond(data: Any, status_code: int = 200) -> FakeHTTPResponse:
    status_error = None
    if status_code >= 400:
        status_error = HTTPClientStatusError(f"{status_code} Server Error")
    return FakeHTTPResponse(
        status_code=status_code,
        json_result=data,
        text=(f"Error {status_code}" if status_code >= 400 else (data if isinstance(data, str) else json.dumps(data))),
        status_error=status_error,
    )


def _mock_api(
    check: ControlMCheck,
    *,
    servers: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
    jobs_total: int | None = None,
    server_status: int = 200,
    jobs_status: int = 200,
    login_token: str = "test-session-token",
    login_status: int = 200,
    reject_first_server_call: bool = False,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "servers": servers if servers is not None else [],
        "jobs": jobs if jobs is not None else [],
        "jobs_total": jobs_total,
    }
    api_endpoint = check.instance["control_m_api_endpoint"].rstrip("/")
    server_url = f"{api_endpoint}/config/servers"
    query = {
        "limit": int(check.instance.get("job_status_limit", 10000)),
        "jobname": check.instance.get("job_name_filter", "*"),
    }
    jobs_url = f"{api_endpoint}/run/jobs/status?{urlencode(query)}"
    login_url = f"{api_endpoint}/session/login"
    if reject_first_server_call:
        check.http.register_response("GET", server_url, _respond(None, 401))

    jobs_payload: dict[str, Any] = {"statuses": state["jobs"]}
    if state["jobs_total"] is not None:
        jobs_payload["total"] = state["jobs_total"]
    for _ in range(10):
        check.http.register_response("GET", server_url, _respond(state["servers"], server_status))
        check.http.register_response("GET", jobs_url, _respond(jobs_payload, jobs_status))
        check.http.register_response("POST", login_url, _respond({"token": login_token}, login_status))
    return state


def _load_job(fixture: str, **overrides: Any) -> dict[str, Any]:
    job = json.loads((FIXTURE_DIR / fixture).read_text())
    job.update(overrides)
    return job


def _make_check(instance: dict[str, Any]) -> ControlMCheck:
    return ControlMCheck("control_m", {}, [instance])


def _run_check(check: ControlMCheck) -> None:
    check.check(None)
