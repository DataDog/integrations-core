# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading

import pytest

from datadog_checks.pan_firewall.collectors import COLLECTORS
from datadog_checks.pan_firewall.collectors.base import Sample
from datadog_checks.pan_firewall.collectors.jobs import JOBS_PENDING_CMD
from datadog_checks.pan_firewall.errors import PanosApiError, PanosUnreachable
from datadog_checks.pan_firewall.poller import FirewallPoller

from .common import (
    BASE_TAGS,
    FIXTURES,
    FW_A_IP,
    FW_A_SERIAL,
    FW_A_TAGS,
    FW_B_IP,
    FW_C_IP,
    INTERFACE_ALL_CMD,
    INTERFACE_CONFIG_CMD,
    STUBS,
    SYSTEM_INFO_CMD,
)
from .fake_panos import FAILURES, FIREWALL_SETS
from .fixture_map import NO_CAPTURE
from .helpers import can_connect_by_ip, make_instance, new_check, register_stubs, stub_runs, stub_sample

# These tests run the poller with the stub collectors they register.
pytestmark = [pytest.mark.unit, pytest.mark.stub_collectors]


def warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


def test_good_run_collects_identity_and_reports_connected(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check())

    aggregator.assert_metric('pan_firewall.can_connect', value=1, tags=FW_A_TAGS, metric_type=aggregator.GAUGE, count=1)
    aggregator.assert_metric(
        'pan_firewall.api.authentication.status', value=0, tags=FW_A_TAGS, metric_type=aggregator.GAUGE, count=1
    )
    # The key is generated first and the jobs check comes before any read; the order of the identity reads is free.
    calls = [(c.type, c.cmd, c.key_sent) for c in fake_panos.calls]
    assert calls[:2] == [('keygen', None, False), ('op', JOBS_PENDING_CMD, True)]
    assert {cmd for _, cmd, _ in calls[2:]} == {SYSTEM_INFO_CMD, INTERFACE_ALL_CMD, INTERFACE_CONFIG_CMD}
    assert all(key_sent for _, _, key_sent in calls[1:])


# Transport failures, and HTTP errors whose body is not a PAN-OS response: none of them means the firewall API answered,
# and none of them says anything about the credentials.
@pytest.mark.parametrize('failure', ['timeout', 'html_403'])
def test_unreachable_on_first_run_reports_disconnected_without_device_id(dd_run_check, aggregator, fake_panos, failure):
    fake_panos.fail(FW_A_IP, failure)
    check = new_check()

    dd_run_check(check)

    aggregator.assert_metric('pan_firewall.can_connect', value=0, tags=BASE_TAGS, metric_type=aggregator.GAUGE, count=1)
    # Nothing has said whether the credentials work yet.
    assert aggregator.metrics('pan_firewall.api.authentication.status') == []


def test_auth_status_is_sent_from_the_first_answer(dd_run_check, aggregator, fake_panos, schedule_clock):
    fake_panos.fail(FW_A_IP, 'timeout')
    check = new_check()
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)
    aggregator.reset()
    # The identity read that failed is retried after 5 minutes; wait for it so the tags carry the device_id.
    schedule_clock.now += 300

    dd_run_check(check)

    aggregator.assert_metric(
        'pan_firewall.api.authentication.status', value=0, tags=FW_A_TAGS, metric_type=aggregator.GAUGE, count=1
    )


def test_outage_after_restart_keeps_device_id(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check())
    fake_panos.fail(FW_A_IP, 'refused')
    aggregator.reset()

    # A new check instance with the same config shares the persistent cache, as after an Agent restart.
    dd_run_check(new_check())

    aggregator.assert_metric('pan_firewall.can_connect', value=0, tags=FW_A_TAGS, metric_type=aggregator.GAUGE, count=1)


def test_identity_without_interface_capture(dd_run_check, aggregator):
    # fw-b has no `show interface all` capture, so the fake answers it with an error.
    dd_run_check(new_check(make_instance(ip=FW_B_IP)))

    (metric,) = aggregator.metrics('pan_firewall.can_connect')
    assert metric.value == 1
    assert {'device_id:007900000000002', 'device_hostname:fw-b'} <= set(metric.tags)


def interface_reads(fake_panos, since=0):
    return sum(1 for c in fake_panos.calls[since:] if c.cmd == INTERFACE_ALL_CMD)


@pytest.mark.parametrize(
    'cmd, answer, prefix',
    [
        pytest.param(INTERFACE_ALL_CMD, (200, NO_CAPTURE), 'cannot read the interfaces,', id='interfaces'),
        pytest.param(
            INTERFACE_CONFIG_CMD,
            (403, (FIXTURES / 'fw-a-probe' / 'config_refused.xml').read_bytes()),
            'cannot read the interface config',
            id='interface-config',
        ),
    ],
)
def test_a_lasting_identity_read_failure_is_warned_once(
    dd_run_check, fake_panos, schedule_clock, caplog, cmd, answer, prefix
):
    # The read is retried every identity interval; a failure that lasts must not warn on every retry.
    fake_panos.answer_op(FW_A_IP, cmd, answer)
    caplog.set_level('DEBUG')
    check = new_check()

    dd_run_check(check)
    schedule_clock.now += 1800
    dd_run_check(check)

    failures = [r for r in caplog.records if r.getMessage().startswith(f'{FW_A_IP}: {prefix}')]
    assert [r.levelname for r in failures] == ['WARNING', 'DEBUG']


def test_interface_read_is_retried_within_five_minutes_until_it_answers(dd_run_check, fake_panos, schedule_clock):
    check = new_check(make_instance(ip=FW_B_IP))
    start = schedule_clock.now
    dd_run_check(check)
    assert interface_reads(fake_panos) == 1

    schedule_clock.now = start + 240
    calls_before = len(fake_panos.calls)
    dd_run_check(check)
    assert interface_reads(fake_panos, calls_before) == 0

    schedule_clock.now = start + 300
    calls_before = len(fake_panos.calls)
    dd_run_check(check)
    assert interface_reads(fake_panos, calls_before) == 1


def test_failed_interface_read_after_a_good_one_waits_the_identity_interval(dd_run_check, fake_panos, schedule_clock):
    check = new_check()
    start = schedule_clock.now
    dd_run_check(check)
    fake_panos.answer_op(FW_A_IP, INTERFACE_ALL_CMD, (200, NO_CAPTURE))

    schedule_clock.now = start + 1800
    dd_run_check(check)
    schedule_clock.now = start + 2100
    calls_before = len(fake_panos.calls)
    dd_run_check(check)

    assert interface_reads(fake_panos, calls_before) == 0


@pytest.mark.parametrize(
    'on',
    [
        pytest.param('keygen', id='keygen-rejected'),
        pytest.param('api', id='key-rejected-again-after-good-keygen'),
    ],
)
def test_rejected_credentials_are_reported(dd_run_check, aggregator, fake_panos, on):
    fake_panos.fail(FW_A_IP, 'http_403', on=on)

    dd_run_check(new_check())

    assert aggregator.metrics('pan_firewall.api.authentication.status')[0].value == 1
    # The firewall answered, even if only to refuse the credentials.
    assert aggregator.metrics('pan_firewall.can_connect')[0].value == 1


def auth_statuses(aggregator):
    return [m.value for m in aggregator.metrics('pan_firewall.api.authentication.status')]


def test_run_without_an_auth_verdict_sends_no_auth_status(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(FW_A_IP, 'http_403', on='keygen')
    check = new_check()
    dd_run_check(check)
    # The keygen times out: nothing says whether the password is right now.
    fake_panos.fail(FW_A_IP, 'timeout', on='keygen')
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)

    dd_run_check(check)

    assert auth_statuses(aggregator) == [1, 0]
    assert [m.value for m in aggregator.metrics('pan_firewall.can_connect')] == [1, 0, 1]


def test_static_key_accepted_again_clears_the_auth_status(dd_run_check, aggregator, fake_panos):
    check = new_check(make_instance(firewall_credentials=[{'api_key': 'dummy-api-key'}]))
    fake_panos.fail(FW_A_IP, 'http_403', on='api')
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)

    dd_run_check(check)

    assert auth_statuses(aggregator) == [1, 0]
    assert [c for c in fake_panos.calls if c.type == 'keygen'] == []


def test_run_with_nothing_due_makes_no_call_and_sends_no_health_metric(dd_run_check, aggregator, fake_panos):
    check = new_check()
    dd_run_check(check)
    calls = len(fake_panos.calls)
    aggregator.reset()

    dd_run_check(check)

    assert len(fake_panos.calls) == calls
    assert aggregator.metrics('pan_firewall.can_connect') == []
    assert aggregator.metrics('pan_firewall.api.authentication.status') == []


def test_collector_timers_count_from_the_start_of_the_run(
    dd_run_check, aggregator, fake_panos, monkeypatch, schedule_clock
):
    # The Agent starts runs on a fixed 60 s grid: timers counted from the end of a run that takes 2 s would make the
    # run at 120 s too early for `bgp` (every 120 s), and delay it to 180 s.
    def bgp(ctx):
        schedule_clock.now += 2
        return [stub_sample('bgp')]

    register_stubs(monkeypatch, bgp=bgp)
    check = new_check()
    start = schedule_clock.now
    bgp_runs = []

    for offset in (0, 60, 120):
        schedule_clock.now = start + offset
        aggregator.reset()
        dd_run_check(check)
        if (FW_A_IP, 'bgp') in stub_runs(aggregator):
            bgp_runs.append(offset)

    assert bgp_runs == [0, 120]


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

    monkeypatch.setitem(COLLECTORS, 'bgp', collect)

    dd_run_check(new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP, FW_C_IP], max_concurrency=2)))

    assert peak == 2
    assert stub_runs(aggregator) == {(FW_A_IP, 'bgp'), (FW_B_IP, 'bgp'), (FW_C_IP, 'bgp')}


def test_unreachable_firewall_skips_the_remaining_collectors_of_that_firewall_only(
    dd_run_check, aggregator, fake_panos, monkeypatch, caplog
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
    fake_panos.answer_op(FW_A_IP, SYSTEM_INFO_CMD, FAILURES['timeout'])
    aggregator.reset()
    caplog.clear()
    calls_before = len(fake_panos.calls_to(FW_A_IP))

    dd_run_check(check)

    assert stub_runs(aggregator) == {(FW_B_IP, name) for name in STUBS}
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1, FW_B_IP: 1}
    # The jobs check and the one call that failed: nothing else reached the firewall.
    assert len(fake_panos.calls_to(FW_A_IP)) - calls_before == 2
    # The one test that pins the whole message; the others check its parts.
    assert warnings(caplog) == [
        f'{FW_A_IP}: could not reach the firewall (timed out) during bgp; '
        'skipped for this run: dataplane, interfaces, system_resources'
    ]

    # The skipped collectors stay due; the one that failed waits for its interval.
    fake_panos.recover(FW_A_IP)
    aggregator.reset()
    dd_run_check(check)

    assert stub_runs(aggregator) == {(FW_A_IP, name) for name in ('dataplane', 'interfaces', 'system_resources')}


def test_identity_timeout_skips_every_collector(dd_run_check, aggregator, fake_panos, monkeypatch):
    dd_run_check(new_check())
    register_stubs(monkeypatch)
    fake_panos.answer_op(FW_A_IP, SYSTEM_INFO_CMD, FAILURES['timeout'])
    aggregator.reset()

    # After a restart, the identity comes from the cache and is refreshed right after the jobs check.
    dd_run_check(new_check())

    assert stub_runs(aggregator) == set()
    # The jobs check answered.
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1}


def raise_(error):
    raise error


@pytest.mark.parametrize(
    'bgp',
    [
        pytest.param(lambda ctx: raise_(ValueError('unexpected shape')), id='bug'),
        pytest.param(lambda ctx: raise_(PanosApiError('400', 'bad command')), id='api-error'),
        # Submitting it fails, after the collector returned.
        pytest.param(lambda ctx: [Sample('stub', 1, (), 'unknown')], id='malformed-sample'),  # type: ignore[arg-type]
    ],
)
def test_failing_collector_does_not_stop_the_others(dd_run_check, aggregator, monkeypatch, bgp):
    register_stubs(monkeypatch, bgp=bgp)

    dd_run_check(new_check())

    assert stub_runs(aggregator) == {(FW_A_IP, name) for name in STUBS if name != 'bgp'}
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1}


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
    monkeypatch.setitem(COLLECTORS, 'bgp', bgp)
    fake_panos.answer_op(FW_A_IP, SYSTEM_INFO_CMD, FAILURES['timeout'])
    caplog.clear()

    dd_run_check(check)

    (warning,) = warnings(caplog)
    assert warning.startswith(f'{FW_A_IP}: could not reach the firewall (timed out)')


def test_unexpected_poller_error_does_not_stop_other_firewalls(dd_run_check, aggregator, monkeypatch):
    run = FirewallPoller.run

    def failing_run(self):
        if self.ip == FW_B_IP:
            raise RuntimeError('boom')
        run(self)

    monkeypatch.setattr(FirewallPoller, 'run', failing_run)

    dd_run_check(new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP])))

    assert can_connect_by_ip(aggregator) == {FW_A_IP: 1}


@pytest.mark.parametrize(
    'options, expected',
    [
        pytest.param({}, (30, 30), id='default-30s'),
        pytest.param({'timeout': 5}, (5, 5), id='configured'),
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


@pytest.mark.parametrize('cached', ['not json', '{"unknown": 1}'], ids=['not-json', 'unknown-field'])
def test_unreadable_cached_identity_is_ignored(dd_run_check, aggregator, fake_panos, cached):
    fake_panos.fail(FW_A_IP, 'refused')
    check = new_check()
    # The cache id comes from the configuration, which the first run loads.
    dd_run_check(check)
    check.write_persistent_cache(f'identity:{FW_A_IP}', cached)
    aggregator.reset()

    # A restart reads the cache.
    dd_run_check(new_check())

    aggregator.assert_metric('pan_firewall.can_connect', value=0, tags=BASE_TAGS, count=1)


def test_system_info_without_serial_keeps_the_cached_identity(dd_run_check, aggregator, fake_panos, monkeypatch):
    dd_run_check(new_check())
    no_serial = b'<response status="success"><result><system><hostname>other</hostname></system></result></response>'
    monkeypatch.setitem(FAILURES, 'no_serial', (200, no_serial))
    fake_panos.fail(FW_A_IP, 'no_serial', on='api')
    aggregator.reset()

    # A restart loads the cached identity and refreshes it on its first run.
    dd_run_check(new_check())

    aggregator.assert_metric('pan_firewall.can_connect', value=1, tags=FW_A_TAGS, metric_type=aggregator.GAUGE, count=1)
    # The persistent cache still holds the good identity.
    fake_panos.fail(FW_A_IP, 'refused')
    aggregator.reset()
    dd_run_check(new_check())
    aggregator.assert_metric('pan_firewall.can_connect', value=0, tags=FW_A_TAGS, metric_type=aggregator.GAUGE, count=1)


@pytest.mark.parametrize(
    'error',
    [pytest.param(PanosApiError('400', 'bad command'), id='api-error'), pytest.param(ValueError('bug'), id='bug')],
)
def test_failed_collector_is_retried_after_5_minutes_not_after_its_interval(
    dd_run_check, monkeypatch, schedule_clock, error
):
    runs = []

    def licenses(ctx):
        runs.append(schedule_clock.now)
        raise error

    monkeypatch.setitem(COLLECTORS, 'licenses', licenses)
    check = new_check()
    start = schedule_clock.now
    for seconds in (0, 299, 300):
        schedule_clock.now = start + seconds
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

    def reads_identity():
        calls_before = len(fake_panos.calls)
        dd_run_check(check)
        return SYSTEM_INFO_CMD in [c.cmd for c in fake_panos.calls[calls_before:]]

    # Not on every run after the failure, and not after the 30-minute interval either.
    schedule_clock.now += 299
    assert not reads_identity()
    schedule_clock.now += 1
    assert reads_identity()


def test_identity_is_read_again_on_the_next_run_after_the_key_is_regenerated(
    dd_run_check, fake_panos, monkeypatch, schedule_clock
):
    monkeypatch.setitem(COLLECTORS, 'bgp', lambda ctx: [])
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
