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
from datadog_checks.control_m.metrics import (
    build_run_key,
    duration_ms,
    job_metric_tags,
    normalize_status,
    prune_state_map,
    result_from_status,
)

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
    monkeypatch.setattr(check._client, 'request', Mock(return_value=response))


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
def test_normalize_status(raw: str | None, expected: str) -> None:
    assert normalize_status(raw) == expected


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
def test_result_from_status(status: str, expected: str) -> None:
    assert result_from_status(status) == expected


@pytest.mark.parametrize(
    'job, expected',
    [
        ({'startTime': '20260115100000', 'endTime': '20260115103000'}, 1_800_000),
        ({'startTime': 'Jan 15, 2026, 10:00:00 AM', 'endTime': 'Jan 15, 2026, 10:30:00 AM'}, 1_800_000),
        ({'startTime': '20260115100000', 'endTime': '20260115100000'}, 0),
        ({'startTime': ['20260115100000'], 'endTime': ['20260115103000']}, 1_800_000),
    ],
)
def test_duration_ms_valid(job: dict, expected: int) -> None:
    assert duration_ms(job) == expected


@pytest.mark.parametrize(
    'job',
    [
        {'endTime': '20260115103000'},
        {'startTime': '20260115100000'},
        {'startTime': '20260115103000', 'endTime': '20260115100000'},
        {'startTime': [], 'endTime': '20260115103000'},
    ],
)
def test_duration_ms_returns_none(job: dict) -> None:
    assert duration_ms(job) is None


@pytest.mark.parametrize(
    'job, expected_key',
    [
        ({'jobId': 'abc', 'numberOfRuns': 3}, 'abc#3'),
        ({'jobId': 'abc', 'startTime': '20260115100000'}, 'abc#20260115100000'),
        ({'jobId': 'abc', 'endTime': '20260115103000'}, 'abc#20260115103000'),
        ({'jobId': 'abc', 'numberOfRuns': 2, 'startTime': '20260115100000'}, 'abc#2'),
        ({'jobId': 'abc'}, None),
        ({'name': 'no_job_id', 'status': 'Ended OK'}, None),
        ({}, None),
    ],
)
def test_build_run_key(job: dict, expected_key: str | None) -> None:
    assert build_run_key(job) == expected_key


def test_job_metric_tags_full(instance: dict[str, Any], aggregator: AggregatorStub) -> None:
    check = _make_check(instance)
    tags = job_metric_tags(
        check._base_tags, {'ctm': 'srv1', 'name': 'my_job', 'folder': 'my_folder', 'type': 'Command'}
    )
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

    check.gauge('_test', 1, tags=job_metric_tags(check._base_tags, {}))
    aggregator.assert_metric_has_tag('control_m._test', 'ctm_server:unknown')
    with pytest.raises(AssertionError):
        aggregator.assert_metric_has_tag_prefix('control_m._test', 'job_name:')

    aggregator.reset()

    check.gauge('_test', 1, tags=job_metric_tags(check._base_tags, {'server': 'alt_srv'}))
    aggregator.assert_metric_has_tag('control_m._test', 'ctm_server:alt_srv')

    aggregator.reset()

    check.gauge('_test', 1, tags=job_metric_tags(check._base_tags, {'ctm': 'primary', 'server': 'secondary'}))
    aggregator.assert_metric_has_tag('control_m._test', 'ctm_server:primary')


def test_jobs_status_url_defaults_and_custom(instance: dict[str, Any]) -> None:
    check = _make_check(instance)
    url = check._job_collector._jobs_status_url
    assert '/run/jobs/status?' in url
    assert 'limit=10000' in url
    assert 'jobname=%2A' in url

    custom_instance = {
        **instance,
        'job_status_limit': 50,
        'job_name_filter': 'nightly_*',
    }
    check = _make_check(custom_instance)
    url = check._job_collector._jobs_status_url
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
    check._job_collector.collect()

    aggregator.assert_metric('control_m.jobs.total', value=10, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.returned', value=2, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.active', value=2, count=1)
    aggregator.assert_metric('control_m.job.run.count', count=0)
    aggregator.assert_metric('control_m.job.run.duration_ms', count=0)

    aggregator.reset()

    _mock_job_response(check, monkeypatch, [])
    check._job_collector.collect()

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
            {'jobId': 'notimes1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'no_times', 'status': 'Ended OK'},
        ],
    )
    check._job_collector.collect()

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
                'jobId': 'timed1',
                'numberOfRuns': 1,
                'ctm': 'srv1',
                'name': 'timed_job',
                'status': 'Ended OK',
                'startTime': '20260115100000',
                'endTime': '20260115103000',
            },
        ],
    )
    check._job_collector.collect()

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
            {'jobId': 'term_fail', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'job_fail', 'status': 'Ended Not OK'},
            {'jobId': 'term_cancel', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'job_cancel', 'status': 'Cancelled'},
            {'jobId': 'term_ok', 'numberOfRuns': 1, 'server': 'alt_server', 'name': 'job_ok', 'status': 'Ended OK'},
        ],
    )
    check._job_collector.collect()

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
    check._job_collector.collect()

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
    monkeypatch.setattr(check._client, 'request', Mock(return_value=response))
    check._job_collector.collect()
    aggregator.assert_metric('control_m.job.run.count', count=0)

    aggregator.reset()

    base = ['control_m_instance:https://example.com/automation-api']
    _mock_job_response(check, monkeypatch, ["not a dict", None, {'ctm': 'srv1', 'status': 'Executing'}])
    check._job_collector.collect()
    aggregator.assert_metric('control_m.jobs.returned', value=3, tags=base, count=1)
    aggregator.assert_metric('control_m.jobs.active', value=1, count=1)


def test_terminal_job_emitted_once(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    terminal_job = [
        {'jobId': 'dedup1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'j1', 'status': 'Ended OK'},
    ]

    _mock_job_response(check, monkeypatch, terminal_job)
    check._job_collector.collect()
    aggregator.assert_metric('control_m.job.run.count', value=1, count=1)

    aggregator.reset()

    _mock_job_response(check, monkeypatch, terminal_job)
    check._job_collector.collect()
    aggregator.assert_metric('control_m.job.run.count', count=0)


def test_terminal_job_new_run_number(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)

    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'rerun1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'j1', 'status': 'Ended OK'}],
    )
    check._job_collector.collect()
    aggregator.assert_metric('control_m.job.run.count', value=1, count=1)

    aggregator.reset()

    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'rerun1', 'numberOfRuns': 2, 'ctm': 'srv1', 'name': 'j1', 'status': 'Ended OK'}],
    )
    check._job_collector.collect()
    aggregator.assert_metric('control_m.job.run.count', value=1, count=1)


def test_terminal_job_no_dedupe_key_skipped(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    _mock_job_response(
        check,
        monkeypatch,
        [{'ctm': 'srv1', 'name': 'no_id', 'status': 'Ended OK'}],
    )
    check._job_collector.collect()

    aggregator.assert_metric('control_m.job.run.count', count=0)
    aggregator.assert_metric('control_m.jobs.by_status', count=1)


def test_finalized_cache_persisted_and_loaded(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'persist1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'j1', 'status': 'Ended OK'}],
    )
    check._job_collector.collect()
    aggregator.assert_metric('control_m.job.run.count', value=1, count=1)

    check2 = _make_check(instance)
    aggregator.reset()
    _mock_job_response(
        check2,
        monkeypatch,
        [{'jobId': 'persist1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'j1', 'status': 'Ended OK'}],
    )
    check2._job_collector.collect()
    aggregator.assert_metric('control_m.job.run.count', count=0)


def test_finalized_prune_removes_expired() -> None:
    now = time.time()
    state_map = {
        'fresh_key': now - 100,
        'stale_key': now - 100_000,
    }
    changed = prune_state_map(state_map, now, 86400)
    assert changed is True
    assert 'fresh_key' in state_map
    assert 'stale_key' not in state_map


def test_active_runs_cleaned_on_terminal(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)

    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'active1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'j1', 'status': 'Executing'}],
    )
    check._job_collector.collect()
    assert 'active1#1' in check._job_collector._active_runs

    aggregator.reset()

    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'active1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'j1', 'status': 'Ended OK'}],
    )
    check._job_collector.collect()
    assert 'active1#1' not in check._job_collector._active_runs
    assert 'active1#1' in check._job_collector._finalized_runs
    aggregator.assert_metric('control_m.job.run.count', value=1, count=1)


def test_events_disabled_by_default(
    instance: dict[str, Any],
    aggregator: AggregatorStub,
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(instance)
    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'ev1', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'fail_job', 'status': 'Ended Not OK'}],
    )
    check._job_collector.collect()

    aggregator.assert_metric('control_m.job.run.count', count=1)
    assert len(aggregator.events) == 0


def test_event_on_failure(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
    }
    check = _make_check(inst)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {
                'jobId': 'ev2',
                'numberOfRuns': 1,
                'ctm': 'srv1',
                'name': 'fail_job',
                'folder': 'nightly',
                'status': 'Ended Not OK',
            }
        ],
    )
    check._job_collector.collect()

    assert len(aggregator.events) == 1
    aggregator.assert_event(
        '**Result:** failed',
        exact_match=False,
        msg_title='Control-M job failed: fail_job',
        alert_type='error',
        event_type='control_m.job.completion',
    )


def test_event_on_cancellation(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
    }
    check = _make_check(inst)
    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'ev3', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'cancel_job', 'status': 'Cancelled'}],
    )
    check._job_collector.collect()

    assert len(aggregator.events) == 1
    aggregator.assert_event(
        '**Result:** canceled',
        exact_match=False,
        msg_title='Control-M job canceled: cancel_job',
        alert_type='warning',
    )


def test_event_success_suppressed_by_default(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
    }
    check = _make_check(inst)
    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'ev4', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'ok_job', 'status': 'Ended OK'}],
    )
    check._job_collector.collect()

    aggregator.assert_metric('control_m.job.run.count', count=1)
    assert len(aggregator.events) == 0


def test_event_success_when_opted_in(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
        'emit_success_events': True,
    }
    check = _make_check(inst)
    _mock_job_response(
        check,
        monkeypatch,
        [{'jobId': 'ev5', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'ok_job', 'status': 'Ended OK'}],
    )
    check._job_collector.collect()

    assert len(aggregator.events) == 1
    aggregator.assert_event(
        '**Result:** ok',
        exact_match=False,
        msg_title='Control-M job ok: ok_job',
        alert_type='success',
    )


def test_slow_run_event(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
        'slow_run_threshold_ms': 60000,
    }
    check = _make_check(inst)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {
                'jobId': 'ev6',
                'numberOfRuns': 1,
                'ctm': 'srv1',
                'name': 'slow_job',
                'status': 'Ended OK',
                'startTime': '20260115100000',
                'endTime': '20260115103000',
            }
        ],
    )
    check._job_collector.collect()

    # Success event suppressed (emit_success_events=False), but slow run event fires
    assert len(aggregator.events) == 1
    aggregator.assert_event(
        '**Result:** ok',
        exact_match=False,
        event_type='control_m.job.slow_run',
        alert_type='warning',
    )
    assert '1800000ms' in aggregator.events[0]['msg_title']


def test_slow_run_below_threshold_no_event(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
        'slow_run_threshold_ms': 9999999,
    }
    check = _make_check(inst)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {
                'jobId': 'ev7',
                'numberOfRuns': 1,
                'ctm': 'srv1',
                'name': 'fast_job',
                'status': 'Ended OK',
                'startTime': '20260115100000',
                'endTime': '20260115100001',
            }
        ],
    )
    check._job_collector.collect()

    assert len(aggregator.events) == 0


def test_event_includes_high_cardinality_in_text(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
    }
    check = _make_check(inst)
    _mock_job_response(
        check,
        monkeypatch,
        [
            {
                'jobId': 'wb:0042',
                'numberOfRuns': 3,
                'ctm': 'srv1',
                'name': 'fail_job',
                'folder': 'nightly',
                'status': 'Ended Not OK',
                'startTime': '20260115100000',
                'endTime': '20260115103000',
            }
        ],
    )
    check._job_collector.collect()

    assert len(aggregator.events) == 1
    text = aggregator.events[0]['msg_text']
    assert '**Job ID:** wb:0042' in text
    assert '**Run #:** 3' in text
    assert '**Folder:** nightly' in text
    assert '**Start:** 20260115100000' in text
    assert '**Duration:** 1800000ms' in text


def test_event_deduplicated_with_finalized_runs(aggregator: AggregatorStub, monkeypatch: MonkeyPatch) -> None:
    inst = {
        'control_m_api_endpoint': 'https://example.com/automation-api',
        'headers': {'Authorization': 'Bearer test'},
        'emit_job_events': True,
    }
    check = _make_check(inst)
    job = [{'jobId': 'ev_dup', 'numberOfRuns': 1, 'ctm': 'srv1', 'name': 'dup_job', 'status': 'Ended Not OK'}]

    _mock_job_response(check, monkeypatch, job)
    check._job_collector.collect()
    assert len(aggregator.events) == 1

    aggregator.reset()

    _mock_job_response(check, monkeypatch, job)
    check._job_collector.collect()
    assert len(aggregator.events) == 0


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
    assert check._client._token_refresh_buffer == 10


def test_static_token_401_falls_back_to_session(instance: dict[str, Any], monkeypatch: MonkeyPatch) -> None:
    instance['control_m_username'] = 'user'
    instance['control_m_password'] = 'pass'
    check = _make_check(instance)
    assert check._client.use_session_login is False

    response_401 = Mock(status_code=401)
    monkeypatch.setattr(type(check.http), 'get', lambda self, url, **kwargs: response_401)
    monkeypatch.setattr(check._client, '_session_request', Mock(return_value=Mock(status_code=200)))

    result = check._client.request('get', 'https://example.com/automation-api/config/servers')

    assert check._client.use_session_login is True
    assert check._client._static_token_retry_after > time.monotonic()
    assert result.status_code == 200
    check._client._session_request.assert_called_once()


def test_static_token_401_no_credentials_returns_401(instance: dict[str, Any], monkeypatch: MonkeyPatch) -> None:
    check = _make_check(instance)
    assert check._client._has_credentials is False

    response_401 = Mock(status_code=401)
    monkeypatch.setattr(type(check.http), 'get', lambda self, url, **kwargs: response_401)

    result = check._client.request('get', 'https://example.com/automation-api/config/servers')

    assert result.status_code == 401
    assert check._client.use_session_login is False


def test_static_token_retried_after_cooldown(instance: dict[str, Any], monkeypatch: MonkeyPatch) -> None:
    instance['control_m_username'] = 'user'
    instance['control_m_password'] = 'pass'
    check = _make_check(instance)
    check._client._use_session_login = True
    check._client._static_token_retry_after = time.monotonic() - 1

    response_ok = Mock(status_code=200)
    monkeypatch.setattr(type(check.http), 'get', lambda self, url, **kwargs: response_ok)

    result = check._client.request('get', 'https://example.com/automation-api/config/servers')

    assert check._client.use_session_login is False
    assert result.status_code == 200


def test_session_token_401_triggers_refresh_and_retry(
    session_instance: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(session_instance)
    check._client._token = 'stale-token'
    check._client._token_expiration = time.monotonic() + 9999

    call_count = 0

    def fake_get(self, url, extra_headers=None, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Mock(status_code=401)
        return Mock(status_code=200)

    monkeypatch.setattr(type(check.http), 'get', fake_get)
    monkeypatch.setattr(
        check._client, 'login', Mock(side_effect=lambda: setattr(check._client, '_token', 'fresh-token'))
    )

    result = check._client._session_request(check.http.get, 'https://example.com/automation-api/config/servers')

    assert result.status_code == 200
    assert call_count == 2
    check._client.login.assert_called_once()


def test_session_token_refresh_behavior(session_instance: dict[str, Any]) -> None:
    session_instance['token_refresh_buffer_seconds'] = 300
    check = _make_check(session_instance)
    check._client.login = Mock()
    check._client._token = 'existing-token'

    check._client._token_expiration = time.monotonic() + check._client._token_refresh_buffer + 10
    check._client.ensure_token()
    check._client.login.assert_not_called()

    check._client._token_expiration = time.monotonic() + check._client._token_refresh_buffer - 1
    check._client.ensure_token()
    check._client.login.assert_called_once()


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


def test_session_login_failure_emits_critical_and_gauges(
    dd_run_check: Callable[[AgentCheck, bool], None],
    aggregator: AggregatorStub,
    session_instance: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    check = _make_check(session_instance)
    monkeypatch.setattr(check._client, 'ensure_token', Mock(side_effect=RuntimeError("auth failed")))

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

    monkeypatch.setattr(
        check._client, 'ensure_token', Mock(side_effect=lambda: setattr(check._client, '_token', 'session-token'))
    )
    monkeypatch.setattr(check._client, 'request', Mock(return_value=response))

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

    def mocked_request(method: str, url: str, **kwargs: Any) -> Mock:
        del method, kwargs
        if url.endswith('/config/servers'):
            return servers_response
        if '/run/jobs/status' in url:
            return jobs_response
        raise AssertionError(f'Unexpected URL requested: {url}')

    monkeypatch.setattr(check._client, 'request', mocked_request)

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
