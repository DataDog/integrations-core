# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall.collectors.base import COLLECT_FUNCTIONS, Sample
from datadog_checks.pan_firewall.collectors.jobs import JOBS_PENDING_CMD
from datadog_checks.pan_firewall.errors import PanosApiError, PanosUnreachable
from datadog_checks.pan_firewall.poller import FirewallPoller

from .common import (
    BASE_TAGS,
    FW_A_IP,
    FW_A_SERIAL,
    FW_A_TAGS,
    FW_B_IP,
    FW_B_SERIAL,
    FW_C_IP,
    INTERFACE_ALL_CMD,
    STUBS,
    SYSTEM_INFO_CMD,
)
from .fake_panos import FAILURES, FIREWALL_SETS
from .helpers import can_connect_by_ip, make_instance, new_check, register_stubs, stub_runs, stub_sample


def only_value_and_tags(aggregator, name):
    (metric,) = aggregator.metrics(f'pan_firewall.{name}')
    return metric.value, sorted(metric.tags)


def test_good_run_collects_identity_and_reports_connected(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check())

    assert only_value_and_tags(aggregator, 'can_connect') == (1, FW_A_TAGS)
    assert only_value_and_tags(aggregator, 'api.authentication.status') == (0, FW_A_TAGS)
    assert [(c.type, c.cmd, c.key_sent) for c in fake_panos.calls] == [
        ('keygen', None, False),
        ('op', JOBS_PENDING_CMD, True),
        ('op', SYSTEM_INFO_CMD, True),
        ('op', INTERFACE_ALL_CMD, True),
    ]


# Transport failures, and HTTP errors whose body is not a PAN-OS response: none of them means the firewall API answered,
# and none of them says anything about the credentials.
@pytest.mark.parametrize('failure', ['timeout', 'html_403'])
def test_unreachable_on_first_run_reports_disconnected_without_device_id(dd_run_check, aggregator, fake_panos, failure):
    fake_panos.fail(FW_A_IP, failure)
    check = new_check()

    dd_run_check(check)

    assert only_value_and_tags(aggregator, 'can_connect') == (0, BASE_TAGS)
    assert only_value_and_tags(aggregator, 'api.authentication.status') == (0, BASE_TAGS)


def test_outage_after_restart_keeps_device_id(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check())
    fake_panos.fail(FW_A_IP, 'refused')
    aggregator.reset()

    # A new check instance with the same config shares the persistent cache, as after an Agent restart.
    dd_run_check(new_check())

    assert only_value_and_tags(aggregator, 'can_connect') == (0, FW_A_TAGS)


def test_identity_without_interface_capture(dd_run_check, aggregator, fake_panos):
    # fw-b has no `show interface all` capture, so the fake answers it with an error.
    dd_run_check(new_check(make_instance(ip=FW_B_IP)))

    value, tags = only_value_and_tags(aggregator, 'can_connect')
    assert value == 1
    assert {'device_id:007955000930602', 'device_hostname:fw-b'} <= set(tags)


@pytest.mark.parametrize(
    'on, keygen_only_calls',
    [
        pytest.param('keygen', ['keygen', 'keygen'], id='keygen-rejected'),
        pytest.param('api', None, id='key-rejected-again-after-good-keygen'),
    ],
)
def test_rejected_credentials_are_reported_and_a_rejected_keygen_is_tried_once_per_run(
    dd_run_check, aggregator, fake_panos, on, keygen_only_calls
):
    fake_panos.fail(FW_A_IP, 'http_403', on=on)
    check = new_check()

    dd_run_check(check)

    assert aggregator.metrics('pan_firewall.api.authentication.status')[0].value == 1
    # The firewall answered, even if only to refuse the credentials.
    assert aggregator.metrics('pan_firewall.can_connect')[0].value == 1
    if keygen_only_calls:
        # Only the keygen is rejected, so every call of a run is the keygen: it is tried once per run.
        dd_run_check(check)
        assert [c.type for c in fake_panos.calls] == keygen_only_calls


def auth_statuses(aggregator):
    return [m.value for m in aggregator.metrics('pan_firewall.api.authentication.status')]


def test_run_without_an_auth_verdict_keeps_the_last_auth_status(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(FW_A_IP, 'http_403', on='keygen')
    check = new_check()
    dd_run_check(check)
    # The keygen times out: nothing says whether the password is right now.
    fake_panos.fail(FW_A_IP, 'timeout', on='keygen')
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)

    dd_run_check(check)

    assert auth_statuses(aggregator) == [1, 1, 0]
    assert [m.value for m in aggregator.metrics('pan_firewall.can_connect')] == [1, 0, 1]


def test_static_key_accepted_again_clears_the_auth_status(dd_run_check, aggregator, fake_panos):
    check = new_check(make_instance(firewall_credentials=[{'api_key': 'dummy-api-key'}]))
    fake_panos.fail(FW_A_IP, 'http_403', on='api')
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)

    dd_run_check(check)

    assert auth_statuses(aggregator) == [1, 0]
    assert [c for c in fake_panos.calls if c.type == 'keygen'] == []


def test_nothing_due_repeats_last_status_without_calls(dd_run_check, aggregator, fake_panos):
    check = new_check()
    dd_run_check(check)
    calls = len(fake_panos.calls)
    aggregator.reset()

    dd_run_check(check)

    assert len(fake_panos.calls) == calls
    assert only_value_and_tags(aggregator, 'can_connect') == (1, FW_A_TAGS)
    assert only_value_and_tags(aggregator, 'api.authentication.status') == (0, FW_A_TAGS)


def test_firewalls_are_polled_concurrently_up_to_max_concurrency(dd_run_check, aggregator, monkeypatch):
    monkeypatch.setitem(FIREWALL_SETS, FW_C_IP, 'fw-a')
    lock = threading.Lock()
    in_flight = 0
    peak = 0
    two_in_flight = threading.Event()

    def collect(ctx):
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
            if in_flight == 2:
                two_in_flight.set()
        # Hold this firewall until a second one is being polled at the same time.
        two_in_flight.wait(2)
        with lock:
            in_flight -= 1
        return [stub_sample('bgp')]

    monkeypatch.setitem(COLLECT_FUNCTIONS, 'bgp', collect)

    dd_run_check(new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP, FW_C_IP], max_concurrency=2)))

    assert peak == 2
    assert stub_runs(aggregator) == {(FW_A_IP, 'bgp'), (FW_B_IP, 'bgp'), (FW_C_IP, 'bgp')}


@pytest.mark.parametrize(
    'failure, warning',
    [
        pytest.param('timeout', 'could not reach the firewall (timed out) during bgp', id='timeout'),
    ],
)
def test_unreachable_firewall_skips_the_remaining_collectors_of_that_firewall_only(
    dd_run_check, aggregator, fake_panos, monkeypatch, caplog, failure, warning
):
    check = new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP]))
    # Caches the identity; no collector is registered yet, so the stubs below are all due on the next run.
    dd_run_check(check)
    dataplane_started = threading.Event()
    bgp_failed = threading.Event()

    def bgp(ctx):
        if ctx.identity.serial == FW_A_SERIAL:
            # dataplane is in flight on the other worker when the call fails.
            dataplane_started.wait(5)
            try:
                ctx.client.op(SYSTEM_INFO_CMD)
            finally:
                bgp_failed.set()
        return [stub_sample('bgp')]

    def dataplane(ctx):
        if ctx.identity.serial == FW_A_SERIAL:
            dataplane_started.set()
            bgp_failed.wait(5)
            # Its call fails fast, without waiting: it is skipped, not the one that timed out.
            ctx.client.op(SYSTEM_INFO_CMD)
        return [stub_sample('dataplane')]

    register_stubs(monkeypatch, bgp=bgp, dataplane=dataplane)
    # Only bgp's call fails: the jobs check before the collectors answers.
    fake_panos.answer_op(FW_A_IP, SYSTEM_INFO_CMD, FAILURES[failure])
    aggregator.reset()
    caplog.clear()
    calls_before = len(fake_panos.calls_to(FW_A_IP))

    dd_run_check(check)

    assert stub_runs(aggregator) == {(FW_B_IP, name) for name in STUBS}
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1, FW_B_IP: 1}
    # The jobs check and the one call that failed: nothing else reached the firewall.
    assert len(fake_panos.calls_to(FW_A_IP)) - calls_before == 2
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [f'{FW_A_IP}: {warning}; skipped for this run: dataplane, interfaces, system_resources']

    # The skipped collectors stay due; the one that failed waits for its interval.
    fake_panos.recover(FW_A_IP)
    aggregator.reset()
    dd_run_check(check)

    assert stub_runs(aggregator) == {(FW_A_IP, name) for name in ('dataplane', 'interfaces', 'system_resources')}


def test_identity_timeout_skips_every_collector(dd_run_check, aggregator, fake_panos, monkeypatch, caplog):
    dd_run_check(new_check())
    register_stubs(monkeypatch)
    fake_panos.answer_op(FW_A_IP, SYSTEM_INFO_CMD, FAILURES['timeout'])
    aggregator.reset()
    caplog.clear()

    # After a restart, the identity comes from the cache and is refreshed right after the jobs check.
    dd_run_check(new_check())

    assert stub_runs(aggregator) == set()
    # The jobs check answered.
    assert only_value_and_tags(aggregator, 'can_connect') == (1, FW_A_TAGS)
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [
        f'{FW_A_IP}: could not reach the firewall (timed out) during identity_metadata; '
        f'skipped for this run: {", ".join(STUBS)}'
    ]


def raise_(error):
    raise error


@pytest.mark.parametrize(
    'bgp, error',
    [
        pytest.param(lambda ctx: raise_(ValueError('unexpected shape')), 'unexpected shape', id='bug'),
        pytest.param(
            lambda ctx: raise_(PanosApiError('400', 'bad command')), 'PAN-OS API error 400: bad command', id='api-error'
        ),
        # Submitting it fails, after the collector returned.
        pytest.param(
            lambda ctx: [Sample('stub', 1, (), 'unknown')],  # type: ignore[arg-type]
            "'PanFirewallCheck' object has no attribute 'unknown'",
            id='malformed-sample',
        ),
    ],
)
def test_failing_collector_does_not_stop_the_others(dd_run_check, aggregator, monkeypatch, caplog, bgp, error):
    register_stubs(monkeypatch, bgp=bgp)

    dd_run_check(new_check())

    assert stub_runs(aggregator) == {(FW_A_IP, name) for name in STUBS if name != 'bgp'}
    assert only_value_and_tags(aggregator, 'can_connect') == (1, FW_A_TAGS)
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [f'{FW_A_IP}: collector bgp failed: {error}']


def test_timeout_a_collector_handles_itself_is_still_reported(dd_run_check, fake_panos, monkeypatch, caplog):
    def bgp(ctx):
        try:
            ctx.client.op(SYSTEM_INFO_CMD)
        except PanosUnreachable:
            pass
        return [stub_sample('bgp')]

    check = new_check()
    # Caches the identity, so bgp is the only due collector on the next run.
    dd_run_check(check)
    monkeypatch.setitem(COLLECT_FUNCTIONS, 'bgp', bgp)
    fake_panos.answer_op(FW_A_IP, SYSTEM_INFO_CMD, FAILURES['timeout'])
    caplog.clear()

    dd_run_check(check)

    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [
        f'{FW_A_IP}: could not reach the firewall (timed out) during a call; skipped for this run: none'
    ]


def test_collector_warnings_name_the_firewall(dd_run_check, monkeypatch, caplog):
    def bgp(ctx):
        ctx.warning('unknown shape %s', 'x')
        return []

    register_stubs(monkeypatch, bgp=bgp)

    dd_run_check(new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP])))

    warnings = {r.getMessage() for r in caplog.records if r.levelno == logging.WARNING}
    assert {f'{ip}: unknown shape x' for ip in (FW_A_IP, FW_B_IP)} <= warnings


def test_unexpected_poller_error_does_not_stop_other_firewalls(dd_run_check, aggregator, monkeypatch, caplog):
    run = FirewallPoller.run

    def failing_run(self):
        if self.ip == FW_B_IP:
            raise RuntimeError('boom')
        run(self)

    monkeypatch.setattr(FirewallPoller, 'run', failing_run)

    dd_run_check(new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP])))

    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1}
    (record,) = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert FW_B_IP in record.getMessage()
    assert record.exc_info is not None


@pytest.mark.parametrize(
    'options, expected',
    [
        pytest.param({'timeout': 5}, (5.0, 5.0), id='configured'),
    ],
)
def test_calls_use_the_instance_timeout(dd_run_check, fake_panos, mocker, options, expected):
    timeouts = set()

    def post(url, **kwargs):
        timeouts.add(kwargs['timeout'])
        return fake_panos.post(url, **kwargs)

    mocker.patch('requests.Session.post', side_effect=post)

    dd_run_check(new_check(make_instance(**options)))

    assert timeouts == {expected}


def test_system_info_without_serial_keeps_the_cached_identity(dd_run_check, aggregator, fake_panos, monkeypatch):
    dd_run_check(new_check())
    no_serial = b'<response status="success"><result><system><hostname>other</hostname></system></result></response>'
    monkeypatch.setitem(FAILURES, 'no_serial', (200, no_serial))
    fake_panos.fail(FW_A_IP, 'no_serial', on='api')
    aggregator.reset()

    # A restart loads the cached identity and refreshes it on its first run.
    dd_run_check(new_check())

    assert only_value_and_tags(aggregator, 'can_connect') == (1, FW_A_TAGS)
    # The persistent cache still holds the good identity.
    fake_panos.fail(FW_A_IP, 'refused')
    aggregator.reset()
    dd_run_check(new_check())
    assert only_value_and_tags(aggregator, 'can_connect') == (0, FW_A_TAGS)


def test_static_firewall_replaced_at_the_same_ip_is_tagged_and_tracked_as_the_new_unit(
    dd_run_check,
    aggregator,
    real_collectors,
    monkeypatch,
    schedule_clock,
):
    watermark_reads = []
    read_cache = PanFirewallCheck.read_persistent_cache
    monkeypatch.setattr(
        PanFirewallCheck,
        'read_persistent_cache',
        lambda self, key: watermark_reads.append(key) or read_cache(self, key),
    )
    check = new_check(make_instance(collect_threats=True))
    dd_run_check(check)
    old_state = check._pollers[FW_A_IP].state
    old_state.warned.add('left over from the old unit')
    # The unit is swapped for another one that answers at the same IP; the identity is due again after 30 minutes.
    monkeypatch.setitem(FIREWALL_SETS, FW_A_IP, 'fw-b')
    schedule_clock.now += 1800
    aggregator.reset()
    watermark_reads.clear()

    dd_run_check(check)

    state = check._pollers[FW_A_IP].state
    assert state is not old_state
    assert not state.warned
    value, tags = only_value_and_tags(aggregator, 'can_connect')
    assert {f'device_id:{FW_B_SERIAL}', f'device_serial:{FW_B_SERIAL}', 'device_hostname:fw-b'} <= set(tags)
    assert f'device_id:{FW_A_SERIAL}' not in tags
    assert f'threat_watermark:{FW_B_SERIAL}' in watermark_reads
    assert f'threat_watermark:{FW_A_SERIAL}' not in watermark_reads


def test_failed_collector_is_retried_after_5_minutes_not_after_its_interval(dd_run_check, monkeypatch, schedule_clock):
    runs = []

    def licenses(ctx):
        runs.append(schedule_clock.now)
        raise PanosApiError('400', 'bad command')

    monkeypatch.setitem(COLLECT_FUNCTIONS, 'licenses', licenses)
    check = new_check()
    start = schedule_clock.now
    dd_run_check(check)
    schedule_clock.now += 299
    dd_run_check(check)
    schedule_clock.now += 1

    dd_run_check(check)

    # Licenses run once a day.
    assert runs == [start, start + 300]


def test_failed_identity_read_is_retried_after_5_minutes(dd_run_check, fake_panos, schedule_clock):
    check = new_check()
    dd_run_check(check)
    fake_panos.answer_op(FW_A_IP, SYSTEM_INFO_CMD, FAILURES['html_502'])
    schedule_clock.now += 1800
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)
    schedule_clock.now += 300
    calls_before = len(fake_panos.calls)

    dd_run_check(check)

    # The identity is read every 30 minutes.
    assert SYSTEM_INFO_CMD in [c.cmd for c in fake_panos.calls[calls_before:]]


def test_identity_is_read_again_on_the_next_run_after_the_key_is_regenerated(
    dd_run_check, fake_panos, monkeypatch, schedule_clock
):
    monkeypatch.setitem(COLLECT_FUNCTIONS, 'bgp', lambda ctx: [])
    check = new_check()
    dd_run_check(check)
    # A due collector makes the calls that the firewall now rejects, the key it just regenerated included.
    fake_panos.fail(FW_A_IP, 'http_403', on='api')
    schedule_clock.now += 120
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)
    schedule_clock.now += 120
    calls_before = len(fake_panos.calls)

    dd_run_check(check)

    # The identity is not due for 30 minutes, yet it is read.
    assert SYSTEM_INFO_CMD in [c.cmd for c in fake_panos.calls[calls_before:]]
