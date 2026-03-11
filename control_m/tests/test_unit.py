# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import time
from typing import Any
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch
from requests.exceptions import HTTPError

from datadog_checks.base.stubs.aggregator import AggregatorStub

from .helpers import BASE_TAGS, FIXTURE_DIR, _load_job, _make_check, _mock_api, _respond, _run_check


def test_config_missing_endpoint() -> None:
    with pytest.raises(Exception, match="control_m_api_endpoint.*required"):
        _make_check({"control_m_api_endpoint": ""})


def test_config_token_lifetime_below_minimum() -> None:
    with pytest.raises(Exception, match="token_lifetime_seconds.*at least 60"):
        _make_check(
            {
                "control_m_api_endpoint": "https://x/api",
                "control_m_username": "user",
                "control_m_password": "pass",
                "token_lifetime_seconds": 0,
            }
        )


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
    _mock_api(
        check,
        monkeypatch,
        servers=[{"name": "srv1", "state": "Up"}],
        jobs=[_load_job("job_executing.json")],
    )

    _run_check(check)

    aggregator.assert_metric("control_m.can_connect", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:static_token")
    aggregator.assert_metric("control_m.server.up", value=1, count=1)
    aggregator.assert_metric("control_m.jobs.returned", value=1, count=1)


def test_connect_server_error_emits_critical(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_api(check, monkeypatch, server_status=500)

    with pytest.raises(HTTPError, match="500"):
        _run_check(check)

    aggregator.assert_metric("control_m.can_connect", value=0, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:static_token")


def test_connect_session_login_ok(
    session_instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(session_instance)
    _mock_api(check, monkeypatch, servers=[{"name": "srv1", "state": "Up"}])

    _run_check(check)

    aggregator.assert_metric("control_m.can_login", value=1, count=1)
    aggregator.assert_metric("control_m.can_connect", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:session_login")


def test_connect_session_login_failure_emits_critical(
    session_instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(session_instance)
    _mock_api(check, monkeypatch, login_status=401)

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

    servers = [{"name": "srv1", "state": "Up"}]
    server_call_count = 0

    def handle_get(_self: Any, url: str, **kw: Any) -> Mock:
        nonlocal server_call_count
        if "/config/servers" in url:
            server_call_count += 1
            if server_call_count == 1:
                return _respond(None, 401)
            return _respond(servers)
        if "/run/jobs/status" in url:
            return _respond({"statuses": []})
        return _respond(None, 404)

    def handle_post(_self: Any, url: str, **kw: Any) -> Mock:
        if "/session/login" in url:
            return _respond({"token": "test-session-token"})
        return _respond(None, 404)

    monkeypatch.setattr(type(check.http), "get", handle_get)
    monkeypatch.setattr(type(check.http), "post", handle_post)

    _run_check(check)

    aggregator.assert_metric("control_m.can_connect", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.can_connect", "auth_method:session_login")


def test_server_health_up_and_down(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_api(
        check,
        monkeypatch,
        servers=[
            {"name": "srv_up", "state": "Up"},
            {"name": "srv_down", "state": "Disconnected"},
            {"name": "srv_no_state"},
        ],
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
    _mock_api(
        check,
        monkeypatch,
        jobs=[
            _load_job("job_executing.json"),
            _load_job("job_executing.json"),
        ],
        jobs_total=10,
    )

    _run_check(check)

    aggregator.assert_metric("control_m.jobs.total", value=10, count=1)
    aggregator.assert_metric("control_m.jobs.returned", value=2, count=1)


def test_terminal_ended_ok_with_duration(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_api(
        check,
        monkeypatch,
        jobs=[
            _load_job(
                "job_ended_ok.json",
                jobId="t1",
                name="timed_job",
                startTime="20260115100000",
                endTime="20260115103000",
            )
        ],
    )

    _run_check(check)

    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)
    aggregator.assert_metric_has_tag("control_m.job.run.count", "result:ok")
    aggregator.assert_metric("control_m.job.run.duration_ms", value=1_800_000, count=1)
    aggregator.assert_metric_has_tag("control_m.job.run.duration_ms", "job_name:timed_job")


def test_dedup_same_terminal_job_counted_once(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_api(check, monkeypatch, jobs=[_load_job("job_ended_ok.json", jobId="d1", name="j1")])

    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)

    aggregator.reset()
    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", count=0)


def test_dedup_new_run_number_counted_as_new_completion(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    state = _mock_api(check, monkeypatch, jobs=[_load_job("job_ended_ok.json", jobId="r1", name="j1")])

    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)

    aggregator.reset()
    state["jobs"] = [_load_job("job_ended_ok.json", jobId="r1", name="j1", numberOfRuns=2)]
    _run_check(check)
    aggregator.assert_metric("control_m.job.run.count", value=1, count=1)


def test_events_disabled_by_default(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    check = _make_check(instance)
    _mock_api(check, monkeypatch, jobs=[_load_job("job_ended_not_ok.json", jobId="e1")])

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
    _mock_api(check, monkeypatch, jobs=[_load_job(fixture, jobId=job_id)])

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
    _mock_api(check, monkeypatch, jobs=[_load_job("job_ended_ok.json", jobId="e4", name="ok_job")])

    _run_check(check)

    aggregator.assert_metric("control_m.job.run.count", count=1)
    assert len(aggregator.events) == 0


def test_event_success_when_opted_in(
    instance: dict[str, Any], aggregator: AggregatorStub, monkeypatch: MonkeyPatch
) -> None:
    instance["emit_job_events"] = True
    instance["emit_success_events"] = True
    check = _make_check(instance)
    _mock_api(check, monkeypatch, jobs=[_load_job("job_ended_ok.json", jobId="e5", name="ok_job")])

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
    _mock_api(
        check,
        monkeypatch,
        jobs=[
            _load_job(
                "job_ended_ok.json",
                jobId="e6",
                name="slow_job",
                startTime="20260115100000",
                endTime="20260115103000",
            )
        ],
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
    _mock_api(
        check,
        monkeypatch,
        servers=[
            {"name": "s1", "version": "9.0.21.080"},
            {"name": "s2", "version": "9.1.00.000"},
        ],
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
    _mock_api(
        check,
        monkeypatch,
        servers=servers,
        jobs=jobs_payload["statuses"],
        jobs_total=jobs_payload.get("total"),
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


# estimatedEndTime 2026-02-10 19:04:10 UTC → epoch 1770750250
_ESTIMATED_END_EPOCH = 1770750250.0


@pytest.mark.parametrize(
    "time_offset, expected_value",
    [
        pytest.param(300, 300_000, id="5min_past_estimate"),
        pytest.param(-60, None, id="1min_before_estimate"),
    ],
)
def test_overrun_gauge_given_executing_job(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
    time_offset: int,
    expected_value: int | None,
) -> None:
    monkeypatch.setattr(time, "time", lambda: _ESTIMATED_END_EPOCH + time_offset)

    check = _make_check(instance)
    _mock_api(
        check,
        monkeypatch,
        jobs=[
            _load_job(
                "job_executing.json",
                jobId="wb:overrun1",
                name="late_job",
                folder="nightly",
                startTime="20260210185000",
                estimatedEndTime=["20260210190410"],
            )
        ],
    )

    _run_check(check)

    if expected_value is not None:
        aggregator.assert_metric(
            "control_m.job.overrun_ms",
            value=expected_value,
            tags=BASE_TAGS + ["ctm_server:srv1", "job_name:late_job", "job_id:wb:overrun1", "folder:nightly"],
            count=1,
        )
    else:
        aggregator.assert_metric("control_m.job.overrun_ms", count=0)


@pytest.mark.parametrize(
    "end_time, expected_value",
    [
        pytest.param("20260210191410", 600_000, id="10min_overrun"),
        pytest.param("20260210190000", None, id="within_estimate"),
    ],
)
def test_overrun_histogram_given_terminal_job(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
    end_time: str,
    expected_value: int | None,
) -> None:
    check = _make_check(instance)
    _mock_api(
        check,
        monkeypatch,
        jobs=[
            _load_job(
                "job_ended_ok.json",
                jobId="wb:done1",
                name="finished_job",
                startTime="20260210185000",
                endTime=end_time,
                estimatedEndTime=["20260210190410"],
            )
        ],
    )

    _run_check(check)

    if expected_value is not None:
        aggregator.assert_metric("control_m.job.run.overrun_ms", value=expected_value, count=1)
        aggregator.assert_metric_has_tag("control_m.job.run.overrun_ms", "job_name:finished_job")
        aggregator.assert_metric_has_tag("control_m.job.run.overrun_ms", "result:ok")
    else:
        aggregator.assert_metric("control_m.job.run.overrun_ms", count=0)
