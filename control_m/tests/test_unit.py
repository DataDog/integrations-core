# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch
from requests.exceptions import HTTPError

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.control_m import ControlMCheck

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BASE_TAGS = ["control_m_instance:https://example.com/automation-api"]


class _ApiStub:
    """
    Simulates the Control-M REST API at the HTTP transport boundary when more than one
    response is needed.

    Parameters
    ----------
    servers:
        Servers returned by ``GET /config/servers``.
    jobs:
        Job status entries returned inside ``GET /run/jobs/status``.
    jobs_total:
        Optional ``total`` field in the jobs status payload.
    server_status / jobs_status / login_status:
        HTTP status codes for the corresponding endpoints.
    login_token:
        Token returned by a successful ``POST /session/login``.
    reject_first_server_call:
        When ``True`` the *first* ``GET /config/servers`` returns 401,
        simulating a rejected static token.  Subsequent calls succeed
        normally.  This is purely behavioral — it does not inspect how
        authentication headers are attached.
    """

    def __init__(
        self,
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
        self.servers = servers if servers is not None else []
        self.jobs = jobs if jobs is not None else []
        self.jobs_total = jobs_total
        self.server_status = server_status
        self.jobs_status = jobs_status
        self.login_token = login_token
        self.login_status = login_status
        self._reject_first_server_call = reject_first_server_call
        self._server_call_count = 0

    def get(self, url: str, **kw: Any) -> Mock:
        if "/config/servers" in url:
            self._server_call_count += 1
            if self._reject_first_server_call and self._server_call_count == 1:
                return self._respond(None, 401)
            return self._respond(self.servers, self.server_status)
        if "/run/jobs/status" in url:
            payload: dict[str, Any] = {"statuses": self.jobs}
            if self.jobs_total is not None:
                payload["total"] = self.jobs_total
            return self._respond(payload, self.jobs_status)
        return self._respond(None, 404)

    def post(self, url: str, **kw: Any) -> Mock:
        if "/session/login" in url:
            return self._respond({"token": self.login_token}, self.login_status)
        return self._respond(None, 404)

    @staticmethod
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


def _load_job(fixture: str, **overrides: Any) -> dict[str, Any]:
    job = json.loads((FIXTURE_DIR / fixture).read_text())
    job.update(overrides)
    return job


def _make_check(instance: dict[str, Any]) -> ControlMCheck:
    return ControlMCheck("control_m", {}, [instance])


def _mock_http(check: ControlMCheck, api: _ApiStub, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(type(check.http), "get", lambda self, url, **kw: api.get(url, **kw))
    monkeypatch.setattr(type(check.http), "post", lambda self, url, **kw: api.post(url, **kw))


def _run_check(check: ControlMCheck) -> None:
    check.check(None)


def test_config_missing_endpoint() -> None:
    with pytest.raises(Exception, match="control_m_api_endpoint.*required"):
        _make_check({"control_m_api_endpoint": ""})


def test_config_no_auth() -> None:
    with pytest.raises(Exception, match="No authentication configured"):
        _make_check({"control_m_api_endpoint": "https://x/api"})


@pytest.mark.parametrize(
    "partial",
    [
        {"control_m_username": "user"},
        {"control_m_password": "pass"},
    ],
)
def test_config_partial_credentials(partial: dict[str, str]) -> None:
    with pytest.raises(Exception, match="must both be set"):
        _make_check({"control_m_api_endpoint": "https://x/api", **partial})


def test_connect_ok_with_static_token(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(
            servers=[{"name": "srv1", "state": "Up"}],
            jobs=[_load_job("job_executing.json")],
        ),
        monkeypatch,
    )

    _run_check(check)

    aggregator.assert_metric("control_m.can_connect", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:static_token")
    aggregator.assert_metric("control_m.server.up", value=1, count=1)
    aggregator.assert_metric("control_m.jobs.returned", value=1, count=1)
    assert len(aggregator.events) == 0


def test_connect_server_error_emits_critical(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_http(check, _ApiStub(server_status=500), monkeypatch)

    with pytest.raises(HTTPError, match="500"):
        _run_check(check)

    aggregator.assert_metric("control_m.can_connect", value=0, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:static_token")


def test_connect_session_login_ok(
    session_instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(session_instance)
    _mock_http(check, _ApiStub(servers=[{"name": "srv1", "state": "Up"}]), monkeypatch)

    _run_check(check)

    aggregator.assert_metric("control_m.can_login", value=1, count=1)
    aggregator.assert_metric("control_m.can_connect", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:session_login")
    assert len(aggregator.events) == 0


def test_connect_session_login_failure_emits_critical(
    session_instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(session_instance)
    _mock_http(check, _ApiStub(login_status=401), monkeypatch)

    with pytest.raises(HTTPError, match="401"):
        _run_check(check)

    aggregator.assert_metric("control_m.can_login", value=0, count=1)
    aggregator.assert_metric("control_m.can_connect", value=0, count=1)


def test_connect_static_token_401_falls_back_to_session(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    instance["control_m_username"] = "user"
    instance["control_m_password"] = "pass"
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(servers=[{"name": "srv1", "state": "Up"}], reject_first_server_call=True),
        monkeypatch,
    )

    _run_check(check)

    aggregator.assert_metric("control_m.can_connect", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:session_login")


def test_server_health_up_and_down(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(
            servers=[
                {"name": "srv_up", "state": "Up"},
                {"name": "srv_down", "state": "Disconnected"},
                {"name": "srv_no_state"},
            ]
        ),
        monkeypatch,
    )

    _run_check(check)

    aggregator.assert_metric(
        "control_m.server.up", value=1, tags=BASE_TAGS + ["ctm_server:srv_up", "state:up"], count=1
    )
    aggregator.assert_metric(
        "control_m.server.up", value=0, tags=BASE_TAGS + ["ctm_server:srv_down", "state:disconnected"], count=1
    )
    aggregator.assert_metric(
        "control_m.server.up", value=0, tags=BASE_TAGS + ["ctm_server:srv_no_state", "state:unknown"], count=1
    )


def test_jobs_total_and_returned(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(
            jobs=[
                _load_job("job_executing.json"),
                _load_job("job_executing.json"),
            ],
            jobs_total=10,
        ),
        monkeypatch,
    )

    _run_check(check)

    aggregator.assert_metric("control_m.jobs.total", value=10, count=1)
    aggregator.assert_metric("control_m.jobs.returned", value=2, count=1)
    assert len(aggregator.events) == 0


def test_terminal_ended_ok_with_duration(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(
            jobs=[
                _load_job(
                    "job_ended_ok.json",
                    jobId="t1",
                    name="timed_job",
                    startTime="20260115100000",
                    endTime="20260115103000",
                )
            ]
        ),
        monkeypatch,
    )

    _run_check(check)

    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.job.run.count", "result:ok")
    aggregator.assert_metric("control_m.job.run.duration_ms", value=1_800_000, count=1)
    aggregator.assert_metric_has_tag("control_m.job.run.duration_ms", "job_name:timed_job")
    assert len(aggregator.events) == 0


def test_dedup_same_terminal_job_counted_once(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    api = _ApiStub(jobs=[_load_job("job_ended_ok.json", jobId="d1", name="j1")])
    check = _make_check(instance)
    _mock_http(check, api, monkeypatch)

    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)

    aggregator.reset()
    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", count=0)


def test_dedup_new_run_number_counted_as_new_completion(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    api = _ApiStub(jobs=[_load_job("job_ended_ok.json", jobId="r1", name="j1")])
    check = _make_check(instance)
    _mock_http(check, api, monkeypatch)

    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)

    aggregator.reset()
    api.jobs = [_load_job("job_ended_ok.json", jobId="r1", name="j1", numberOfRuns=2)]
    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)


def test_events_disabled_by_default(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(jobs=[_load_job("job_ended_not_ok.json", jobId="e1")]),
        monkeypatch,
    )

    _run_check(check)

    aggregator.assert_metric("control_m.job.run.count", count=1)
    assert len(aggregator.events) == 0


@pytest.mark.parametrize(
    "fixture, job_id, expected_title, expected_alert_type",
    [
        ("job_ended_not_ok.json", "e2", "Control-M job failed: fail_job", "error"),
        ("job_cancelled.json", "e3", "Control-M job canceled: cancel_job", "warning"),
    ],
)
def test_event_on_terminal_failure(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
    fixture: str,
    job_id: str,
    expected_title: str,
    expected_alert_type: str,
) -> None:
    instance["emit_job_events"] = True
    check = _make_check(instance)
    _mock_http(check, _ApiStub(jobs=[_load_job(fixture, jobId=job_id)]), monkeypatch)

    _run_check(check)

    assert len(aggregator.events) == 1
    aggregator.assert_event(
        "",
        exact_match=False,
        msg_title=expected_title,
        alert_type=expected_alert_type,
        event_type="control_m.job.completion",
    )


def test_event_success_suppressed_by_default(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    instance["emit_job_events"] = True
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(jobs=[_load_job("job_ended_ok.json", jobId="e4", name="ok_job")]),
        monkeypatch,
    )

    _run_check(check)

    aggregator.assert_metric("control_m.job.run.count", count=1)
    assert len(aggregator.events) == 0


def test_event_success_when_opted_in(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    instance["emit_job_events"] = True
    instance["emit_success_events"] = True
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(jobs=[_load_job("job_ended_ok.json", jobId="e5", name="ok_job")]),
        monkeypatch,
    )

    _run_check(check)

    assert len(aggregator.events) == 1
    aggregator.assert_event(
        "Result: ok",
        exact_match=False,
        msg_title="Control-M job ok: ok_job",
        alert_type="success",
    )


def test_event_slow_run_check(instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    instance["emit_job_events"] = True
    instance["slow_run_threshold_ms"] = 60000
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(
            jobs=[
                _load_job(
                    "job_ended_ok.json",
                    jobId="e6",
                    name="slow_job",
                    startTime="20260115100000",
                    endTime="20260115103000",
                )
            ]
        ),
        monkeypatch,
    )

    _run_check(check)

    assert len(aggregator.events) == 1
    aggregator.assert_event(
        "Result: ok",
        exact_match=False,
        event_type="control_m.job.slow_run",
        alert_type="warning",
    )
    assert "1800000ms" in aggregator.events[0]["msg_title"]


def test_metadata_version_from_first_server(
    instance: dict[str, Any], datadog_agent: Any, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(
            servers=[
                {"name": "s1", "version": "9.0.21.080"},
                {"name": "s2", "version": "9.1.00.000"},
            ]
        ),
        monkeypatch,
    )

    _run_check(check)

    datadog_agent.assert_metadata(check.check_id, {"version.raw": "9.0.21.080"})


def test_full_cycle_with_fixture_data(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    datadog_agent: Any,
    monkeypatch: MonkeyPatch,
) -> None:
    servers = json.loads((FIXTURE_DIR / "config_servers_response.txt").read_text())
    jobs_payload = json.loads((FIXTURE_DIR / "jobs_status_response.txt").read_text())

    check = _make_check(instance)
    _mock_http(
        check,
        _ApiStub(
            servers=servers,
            jobs=jobs_payload["statuses"],
            jobs_total=jobs_payload.get("total"),
        ),
        monkeypatch,
    )

    _run_check(check)

    wb_tags = BASE_TAGS + ["ctm_server:workbench"]

    aggregator.assert_metric("control_m.server.up", value=1, tags=BASE_TAGS + ["ctm_server:workbench", "state:up"])
    aggregator.assert_metric("control_m.jobs.total", value=3, tags=BASE_TAGS, count=1)
    aggregator.assert_metric("control_m.jobs.returned", value=3, tags=BASE_TAGS, count=1)
    aggregator.assert_metric("control_m.jobs.active", value=2, tags=wb_tags, count=1)
    aggregator.assert_metric("control_m.jobs.waiting.total", value=1, tags=BASE_TAGS, count=1)
    aggregator.assert_metric("control_m.jobs.waiting.by_server", value=1, tags=wb_tags, count=1)
    aggregator.assert_metric("control_m.jobs.by_status", value=1, tags=wb_tags + ["status:ended_ok"], count=1)
    aggregator.assert_metric("control_m.jobs.by_status", value=1, tags=wb_tags + ["status:wait_condition"], count=1)
    aggregator.assert_metric("control_m.jobs.by_status", value=1, tags=wb_tags + ["status:executing"], count=1)
    aggregator.assert_metric(
        "control_m.job.run.count", value=1, tags=wb_tags + ["job_name:job_ok", "result:ok"], count=1
    )
    aggregator.assert_metric(
        "control_m.job.run.duration_ms", value=60000, tags=wb_tags + ["job_name:job_ok", "result:ok"], count=1
    )

    datadog_agent.assert_metadata(check.check_id, {"version.raw": "9.0.21.080"})
