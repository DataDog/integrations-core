# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from _pytest.monkeypatch import MonkeyPatch

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.control_m import ControlMCheck

FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def _make_check(instance: dict[str, Any]) -> ControlMCheck:
    return ControlMCheck('control_m', {}, [instance])


def _mock_job_response(check, monkeypatch, statuses, total=None):
    payload = {'statuses': statuses}
    if total is not None:
        payload['total'] = total
    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json.return_value = payload
    monkeypatch.setattr(check, '_make_request', Mock(return_value=response))


@pytest.mark.parametrize(
    'raw, expected',
    [
        ('Ended OK', 'ended_ok'),
        ('ended ok', 'ended_ok'),
        ('ENDED OK', 'ended_ok'),
        ('Ended Not OK', 'ended_not_ok'),
        ('Executing', 'executing'),
        ('Wait Condition', 'wait_condition'),
        ('Waiting for Resource', 'wait_resource'),
        ('Cancelled', 'canceled'),
        ('canceled', 'canceled'),
        ('Waiting for Host', 'wait_host'),
        ('Wait Workload', 'wait_workload'),
        (None, 'unknown'),
        ('', 'unknown'),
        ('SomethingNew', 'unknown'),
    ],
)
def test_normalize_status(instance: dict[str, Any], raw: str | None, expected: str) -> None:
    assert _make_check(instance)._normalize_status(raw) == expected


@pytest.mark.parametrize(
    'status, expected',
    [
        ('ended_ok', 'ok'),
        ('ended_not_ok', 'failed'),
        ('canceled', 'canceled'),
        ('executing', 'unknown'),
        ('wait_condition', 'unknown'),
    ],
)
def test_result_from_status(instance: dict[str, Any], status: str, expected: str) -> None:
    assert _make_check(instance)._result_from_status(status) == expected


@pytest.mark.parametrize(
    'job, expected',
    [
        ({'startTime': '20260115100000', 'endTime': '20260115103000'}, 1_800_000),
        ({'startTime': 'Jan 15, 2026, 10:00:00 AM', 'endTime': 'Jan 15, 2026, 10:30:00 AM'}, 1_800_000),
        ({'startTime': '20260115100000', 'endTime': '20260115100000'}, 0),
        ({'startTime': ['20260115100000'], 'endTime': ['20260115103000']}, 1_800_000),
    ],
)
def test_duration_ms_valid(instance: dict[str, Any], job: dict, expected: int) -> None:
    assert _make_check(instance)._duration_ms(job) == expected


@pytest.mark.parametrize(
    'job',
    [
        {'endTime': '20260115103000'},
        {'startTime': '20260115100000'},
        {'startTime': '20260115103000', 'endTime': '20260115100000'},
        {'startTime': [], 'endTime': '20260115103000'},
    ],
)
def test_duration_ms_returns_none(instance: dict[str, Any], job: dict) -> None:
    assert _make_check(instance)._duration_ms(job) is None


def test_job_metric_tags_full(instance: dict[str, Any], aggregator: AggregatorStub) -> None:
    check = _make_check(instance)
    tags = check._job_metric_tags({'ctm': 'srv1', 'name': 'my_job', 'folder': 'my_folder', 'type': 'Command'})
    check.gauge('_test', 1, tags=tags)

    aggregator.assert_metric_has_tags(
        'control_m._test',
        [
            'ctm_server:srv1',
            'job_name:my_job',
            'folder:my_folder',
            'type:command',
        ],
    )


def test_job_metric_tags_minimal_and_server_fallback(instance: dict[str, Any], aggregator: AggregatorStub) -> None:
    check = _make_check(instance)

    check.gauge('_test', 1, tags=check._job_metric_tags({}))
    aggregator.assert_metric_has_tag('control_m._test', 'ctm_server:unknown')
    with pytest.raises(AssertionError):
        aggregator.assert_metric_has_tag_prefix('control_m._test', 'job_name:')

    aggregator.reset()

    check.gauge('_test', 1, tags=check._job_metric_tags({'server': 'alt_srv'}))
    aggregator.assert_metric_has_tag('control_m._test', 'ctm_server:alt_srv')

    aggregator.reset()

    check.gauge('_test', 1, tags=check._job_metric_tags({'ctm': 'primary', 'server': 'secondary'}))
    aggregator.assert_metric_has_tag('control_m._test', 'ctm_server:primary')


def test_build_jobs_status_url_defaults_and_custom(instance: dict[str, Any]) -> None:
    check = _make_check(instance)
    url = check._build_jobs_status_url()
    assert '/run/jobs/status?' in url
    assert 'limit=200' in url
    assert 'jobname=%2A' in url

    custom_instance = {
        **instance,
        'job_status_limit': 50,
        'job_name_filter': 'nightly_*',
    }
    check = _make_check(custom_instance)
    url = check._build_jobs_status_url()
    assert 'limit=50' in url
    assert 'jobname=nightly_%2A' in url


def test_server_health_mixed_states(instance: dict[str, Any], aggregator: AggregatorStub) -> None:
    check = _make_check(instance)
    check._collect_server_health(
        [
            {'name': 'srv_up', 'state': 'Up'},
            {'name': 'srv_down', 'state': 'Disconnected'},
            {'name': 'srv_no_state'},
        ]
    )

    base = ['control_m_instance:https://example.com/automation-api']
    aggregator.assert_metric('control_m.server.up', value=1, tags=base + ['ctm_server:srv_up', 'state:up'])
    aggregator.assert_metric('control_m.server.up', value=0, tags=base + ['ctm_server:srv_down', 'state:disconnected'])
    aggregator.assert_metric('control_m.server.up', value=0, tags=base + ['ctm_server:srv_no_state', 'state:unknown'])


@pytest.mark.parametrize(
    'server_entry, expected_tag',
    [
        ({'name': 'by_name', 'state': 'Up'}, 'ctm_server:by_name'),
        ({'ctm': 'by_ctm', 'state': 'Up'}, 'ctm_server:by_ctm'),
        ({'server': 'by_server', 'state': 'Up'}, 'ctm_server:by_server'),
        ({'state': 'Up'}, 'ctm_server:unknown'),
    ],
)
def test_server_health_name_fallback(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    server_entry: dict,
    expected_tag: str,
) -> None:
    check = _make_check(instance)
    check._collect_server_health([server_entry])

    aggregator.assert_metric('control_m.server.up', count=1)
    aggregator.assert_metric_has_tag('control_m.server.up', expected_tag)


def test_server_health_non_list_is_noop(instance: dict[str, Any], aggregator: AggregatorStub) -> None:
    check = _make_check(instance)
    check._collect_server_health({'error': 'not a list'})

    aggregator.assert_metric('control_m.server.up', count=0)


def test_jobs_no_terminal_emits_only_rollups(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    base = ['control_m_instance:https://example.com/automation-api']
    _mock_job_response(
        check,
        monkeypatch,
        [
            {'ctm': 'srv1', 'status': 'Executing'},
            {'ctm': 'srv1', 'status': 'Executing'},
        ],
        total=10,
    )
    check._collect_job_statuses()

    aggregator.assert_metric('control_m.jobs.total', value=10, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.returned', value=2, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.active', value=2, count=1)
    aggregator.assert_metric('control_m.job.run.count', count=0)
    aggregator.assert_metric('control_m.job.run.duration_ms', count=0)

    aggregator.reset()

    _mock_job_response(check, monkeypatch, [])
    check._collect_job_statuses()

    aggregator.assert_metric('control_m.jobs.returned', value=0, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.total', count=0)
    aggregator.assert_metric('control_m.jobs.active', count=0)
    aggregator.assert_metric('control_m.jobs.by_status', count=0)
    aggregator.assert_metric('control_m.job.run.count', count=0)


def test_jobs_terminal_without_timestamps_emits_count_only(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {'ctm': 'srv1', 'name': 'no_times', 'status': 'Ended OK'},
        ],
    )
    check._collect_job_statuses()

    aggregator.assert_metric('control_m.job.run.count', value=1, count=1)
    aggregator.assert_metric('control_m.job.run.duration_ms', count=0)


def test_jobs_terminal_with_timestamps_emits_duration(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {
                'ctm': 'srv1',
                'name': 'timed_job',
                'status': 'Ended OK',
                'startTime': '20260115100000',
                'endTime': '20260115103000',
            },
        ],
    )
    check._collect_job_statuses()

    aggregator.assert_metric('control_m.job.run.count', value=1, count=1)
    aggregator.assert_metric_has_tag('control_m.job.run.count', 'result:ok')
    aggregator.assert_metric('control_m.job.run.duration_ms', value=1_800_000, count=1)
    aggregator.assert_metric_has_tag('control_m.job.run.duration_ms', 'job_name:timed_job')


def test_jobs_all_terminal_statuses_and_result_tags(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {'ctm': 'srv1', 'name': 'job_fail', 'status': 'Ended Not OK'},
            {'ctm': 'srv1', 'name': 'job_cancel', 'status': 'Cancelled'},
            {'server': 'alt_server', 'name': 'job_ok', 'status': 'Ended OK'},
        ],
    )
    check._collect_job_statuses()

    aggregator.assert_metric('control_m.job.run.count', count=3)
    aggregator.assert_metric_has_tag('control_m.job.run.count', 'result:failed')
    aggregator.assert_metric_has_tag('control_m.job.run.count', 'result:canceled')
    aggregator.assert_metric_has_tag('control_m.job.run.count', 'result:ok')
    aggregator.assert_metric_has_tag('control_m.job.run.count', 'ctm_server:alt_server')


def test_jobs_multiple_servers_rollup(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {'ctm': 'srv_a', 'status': 'Executing'},
            {'ctm': 'srv_a', 'status': 'Wait Condition'},
            {'ctm': 'srv_b', 'status': 'Executing'},
        ],
    )
    check._collect_job_statuses()

    base = ['control_m_instance:https://example.com/automation-api']
    aggregator.assert_metric('control_m.jobs.active', value=2, tags=base + ['ctm_server:srv_a'], count=1)
    aggregator.assert_metric('control_m.jobs.active', value=1, tags=base + ['ctm_server:srv_b'], count=1)
    aggregator.assert_metric('control_m.jobs.waiting.total', value=1, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.waiting.total', value=1, tags=base + ['ctm_server:srv_a'], count=1)


def test_jobs_api_failure_and_bad_entries_handled_gracefully(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)

    response = Mock(status_code=500)
    response.raise_for_status = Mock(side_effect=Exception("server error"))
    monkeypatch.setattr(check, '_make_request', Mock(return_value=response))
    check._collect_job_statuses()
    aggregator.assert_metric('control_m.job.run.count', count=0)

    aggregator.reset()

    base = ['control_m_instance:https://example.com/automation-api']
    _mock_job_response(check, monkeypatch, ["not a dict", None, {'ctm': 'srv1', 'status': 'Executing'}])
    check._collect_job_statuses()
    aggregator.assert_metric('control_m.jobs.returned', value=3, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.active', value=1, count=1)


def test_metadata_version_from_first_server(instance: dict[str, Any], datadog_agent: Any) -> None:
    check = _make_check(instance)
    check._collect_metadata(
        [
            {'name': 's1', 'version': '9.0.21.080'},
            {'name': 's2', 'version': '9.1.00.000'},
        ]
    )
    datadog_agent.assert_metadata(check.check_id, {'version.raw': '9.0.21.080'})


@pytest.mark.parametrize(
    'servers',
    [
        [{'name': 's1'}],
        [],
        {'error': 'unexpected'},
    ],
)
def test_metadata_no_version_found(instance: dict[str, Any], datadog_agent: Any, servers: Any) -> None:
    check = _make_check(instance)
    check._collect_metadata(servers)
    datadog_agent.assert_metadata(check.check_id, {})


@pytest.mark.parametrize(
    'bad_instance, match',
    [
        ({'control_m_api_endpoint': ''}, 'control_m_api_endpoint.*required'),
        ({'control_m_api_endpoint': 'https://x/api'}, 'No authentication configured'),
        ({'control_m_api_endpoint': 'https://x/api', 'control_m_username': 'user'}, 'must both be set'),
        ({'control_m_api_endpoint': 'https://x/api', 'control_m_password': 'pass'}, 'must both be set'),
    ],
)
def test_config_validation_errors(bad_instance: dict, match: str) -> None:
    with pytest.raises(Exception, match=match):
        _make_check(bad_instance)


def test_token_refresh_buffer_clamped_when_exceeds_lifetime(session_instance: dict[str, Any]) -> None:
    session_instance['token_lifetime_seconds'] = 60
    session_instance['token_refresh_buffer_seconds'] = 120
    check = _make_check(session_instance)
    assert check._token_refresh_buffer == 10


def test_static_token_401_falls_back_to_session(instance: dict[str, Any], monkeypatch: MonkeyPatch) -> None:
    instance['control_m_username'] = 'user'
    instance['control_m_password'] = 'pass'
    check = _make_check(instance)
    assert check._use_session_login is False

    response_401 = Mock(status_code=401)
    monkeypatch.setattr(type(check.http), 'get', lambda self, url, **kwargs: response_401)
    monkeypatch.setattr(check, '_make_session_request', Mock(return_value=Mock(status_code=200)))

    result = check._make_request('get', 'https://example.com/automation-api/config/servers')

    assert check._use_session_login is True
    assert check._static_token_retry_after > time.monotonic()
    assert result.status_code == 200
    check._make_session_request.assert_called_once()


def test_static_token_401_no_credentials_returns_401(instance: dict[str, Any], monkeypatch: MonkeyPatch) -> None:
    check = _make_check(instance)
    assert check._has_credentials is False

    response_401 = Mock(status_code=401)
    monkeypatch.setattr(type(check.http), 'get', lambda self, url, **kwargs: response_401)

    result = check._make_request('get', 'https://example.com/automation-api/config/servers')

    assert result.status_code == 401
    assert check._use_session_login is False


def test_static_token_retried_after_cooldown(instance: dict[str, Any], monkeypatch: MonkeyPatch) -> None:
    instance['control_m_username'] = 'user'
    instance['control_m_password'] = 'pass'
    check = _make_check(instance)
    check._use_session_login = True
    check._static_token_retry_after = time.monotonic() - 1

    response_ok = Mock(status_code=200)
    monkeypatch.setattr(type(check.http), 'get', lambda self, url, **kwargs: response_ok)

    result = check._make_request('get', 'https://example.com/automation-api/config/servers')

    assert check._use_session_login is False
    assert result.status_code == 200


def test_session_token_401_triggers_refresh_and_retry(
    session_instance: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(session_instance)
    check._token = 'stale-token'
    check._token_expiration = time.monotonic() + 9999

    call_count = 0

    def fake_get(self, url, extra_headers=None, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Mock(status_code=401)
        return Mock(status_code=200)

    monkeypatch.setattr(type(check.http), 'get', fake_get)
    monkeypatch.setattr(check, '_login', Mock(side_effect=lambda: setattr(check, '_token', 'fresh-token')))

    result = check._make_session_request(check.http.get, 'https://example.com/automation-api/config/servers')

    assert result.status_code == 200
    assert call_count == 2
    check._login.assert_called_once()


def test_session_token_refresh_behavior(session_instance: dict[str, Any]) -> None:
    session_instance['token_refresh_buffer_seconds'] = 300
    check = _make_check(session_instance)
    check._login = Mock()
    check._token = 'existing-token'

    check._token_expiration = time.monotonic() + check._token_refresh_buffer + 10
    check._ensure_token()
    check._login.assert_not_called()

    check._token_expiration = time.monotonic() + check._token_refresh_buffer - 1
    check._ensure_token()
    check._login.assert_called_once()


def test_session_login_failure_emits_critical_and_gauges(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    session_instance: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(session_instance)
    monkeypatch.setattr(check, '_ensure_token', Mock(side_effect=RuntimeError("auth failed")))

    with pytest.raises(Exception):
        dd_run_check(check)

    auth_tags = ['control_m_instance:https://example.com/automation-api', 'auth_method:session_login']
    aggregator.assert_service_check('control_m.can_login', status=AgentCheck.CRITICAL, tags=auth_tags, count=1)
    aggregator.assert_service_check('control_m.can_connect', status=AgentCheck.CRITICAL, tags=auth_tags, count=1)
    aggregator.assert_metric('control_m.can_login', value=0, tags=auth_tags, count=1)
    aggregator.assert_metric('control_m.can_connect', value=0, tags=auth_tags, count=1)


def test_check_can_connect(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    instance: dict[str, Any],
    mock_http_response: Callable[..., Any],
) -> None:
    mock_http_response((FIXTURE_DIR / 'config_servers_response.txt').read_text())
    check = _make_check(instance)
    dd_run_check(check)

    aggregator.assert_service_check('control_m.can_connect', status=AgentCheck.OK, count=1)
    aggregator.assert_metric(
        'control_m.can_connect',
        value=1,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:static_token'],
        count=1,
    )
    aggregator.assert_metric(
        'control_m.server.up',
        value=1,
        tags=[
            'control_m_instance:https://example.com/automation-api',
            'ctm_server:workbench',
            'state:up',
        ],
        count=1,
    )
    aggregator.assert_all_metrics_covered()


def test_check_connectivity_failure_reports_critical(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    instance: dict[str, Any],
    mock_http_response: Callable[..., Any],
) -> None:
    mock_http_response(status_code=500)
    check = _make_check(instance)

    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('control_m.can_connect', status=AgentCheck.CRITICAL, count=1)
    aggregator.assert_metric(
        'control_m.can_connect',
        value=0,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:static_token'],
        count=1,
    )


def test_check_session_login_mode(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    session_instance: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(session_instance)

    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json.return_value = [{'name': 'workbench', 'state': 'Up', 'version': '9.0.21.080'}]

    monkeypatch.setattr(check, '_ensure_token', Mock(side_effect=lambda: setattr(check, '_token', 'session-token')))
    monkeypatch.setattr(check, '_make_request', Mock(return_value=response))

    dd_run_check(check)

    aggregator.assert_service_check(
        'control_m.can_login',
        status=AgentCheck.OK,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:session_login'],
        count=1,
    )
    aggregator.assert_service_check(
        'control_m.can_connect',
        status=AgentCheck.OK,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:session_login'],
        count=1,
    )
    aggregator.assert_metric(
        'control_m.can_connect',
        value=1,
        tags=['control_m_instance:https://example.com/automation-api', 'auth_method:session_login'],
        count=1,
    )


def test_check_collects_core_job_telemetry(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    instance: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)

    servers_payload = (FIXTURE_DIR / 'config_servers_response.txt').read_text()
    jobs_payload = json.loads((FIXTURE_DIR / 'jobs_status_response.txt').read_text())

    servers_response = Mock()
    servers_response.status_code = 200
    servers_response.raise_for_status = Mock()
    servers_response.json.return_value = json.loads(servers_payload)

    jobs_response = Mock()
    jobs_response.status_code = 200
    jobs_response.raise_for_status = Mock()
    jobs_response.json.return_value = jobs_payload

    def mocked_make_request(method: str, url: str, **kwargs: Any) -> Mock:
        del method, kwargs
        if url.endswith('/config/servers'):
            return servers_response
        if '/run/jobs/status' in url:
            return jobs_response
        raise AssertionError(f'Unexpected URL requested: {url}')

    monkeypatch.setattr(check, '_make_request', mocked_make_request)

    dd_run_check(check)

    base_tags = ['control_m_instance:https://example.com/automation-api']
    workbench_tags = base_tags + ['ctm_server:workbench']

    aggregator.assert_metric('control_m.jobs.total', value=3, tags=base_tags, count=1)
    aggregator.assert_metric('control_m.jobs.returned', value=3, tags=base_tags, count=1)
    aggregator.assert_metric('control_m.jobs.active', value=2, tags=workbench_tags, count=1)
    aggregator.assert_metric('control_m.jobs.waiting.total', value=1, tags=base_tags, count=1)
    aggregator.assert_metric('control_m.jobs.by_status', value=1, tags=workbench_tags + ['status:ended_ok'], count=1)
    aggregator.assert_metric(
        'control_m.jobs.by_status', value=1, tags=workbench_tags + ['status:wait_condition'], count=1
    )
    aggregator.assert_metric('control_m.jobs.by_status', value=1, tags=workbench_tags + ['status:executing'], count=1)
    aggregator.assert_metric(
        'control_m.job.run.count', value=1, tags=workbench_tags + ['job_name:job_ok', 'result:ok'], count=1
    )
    aggregator.assert_metric(
        'control_m.job.run.duration_ms', value=60000, tags=workbench_tags + ['job_name:job_ok', 'result:ok'], count=1
    )
