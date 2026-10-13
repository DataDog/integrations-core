# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import re
import threading

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, Sample
from datadog_checks.pan_firewall.errors import PanosApiError
from datadog_checks.pan_firewall.poller import FirewallPoller

from .common import CREDENTIALS
from .fake_panos import FAILURES, FIREWALL_SETS

FW_A_IP = '192.0.2.10'
FW_B_IP = '192.0.2.11'
FW_C_IP = '192.0.2.12'
FW_A_SERIAL = '007955000930601'
STUBS = ('bgp', 'dataplane', 'interfaces', 'system_resources')
SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
INTERFACE_ALL_CMD = '<show><interface>all</interface></show>'

BASE_TAGS = [f'device_ip:{FW_A_IP}', 'device_namespace:default', 'device_vendor:paloaltonetworks', 'team:test']
FW_A_TAGS = sorted(
    [
        *BASE_TAGS,
        f'device_id:{FW_A_SERIAL}',
        'device_hostname:fw-a',
        f'device_serial:{FW_A_SERIAL}',
        'device_model:PA-VM',
        'device_family:vm',
        'os_version:11.1.13-h12',
        'multi_vsys:false',
        'advanced_routing:false',
        f'dd.internal.resource:ndm_device:{FW_A_SERIAL}',
        f'dd.internal.resource:ndm_device_user_tags:{FW_A_SERIAL}',
    ]
)


def make_instance(ip=FW_A_IP, **options):
    return {'firewalls': [ip], 'firewall_credentials': copy.deepcopy(CREDENTIALS), 'tags': ['team:test'], **options}


def new_check(instance=None):
    return PanFirewallCheck('pan_firewall', {}, [instance or make_instance()])


def only_value_and_tags(aggregator, name):
    (metric,) = aggregator.metrics(f'pan_firewall.{name}')
    return metric.value, sorted(metric.tags)


def stub_sample(name):
    return Sample('stub', 1, (f'collector:{name}',), 'gauge')


def register_stubs(monkeypatch, **overrides):
    """Register a stub for each name in STUBS that submits `pan_firewall.stub` tagged `collector:<name>`."""
    for name in STUBS:
        monkeypatch.setitem(COLLECT_FUNCTIONS, name, overrides.get(name, lambda ctx, name=name: [stub_sample(name)]))


def stub_runs(aggregator):
    """The (device_ip, collector) pairs that submitted a stub sample."""
    runs = set()
    for metric in aggregator.metrics('pan_firewall.stub'):
        tags = dict(tag.split(':', 1) for tag in metric.tags if tag.startswith(('device_ip:', 'collector:')))
        runs.add((tags['device_ip'], tags['collector']))
    return runs


def can_connect_by_ip(aggregator):
    return {
        next(t.split(':', 1)[1] for t in m.tags if t.startswith('device_ip:')): m.value
        for m in aggregator.metrics('pan_firewall.can_connect')
    }


def test_good_run_collects_identity_and_reports_connected(dd_run_check, aggregator, fake_panos, caplog):
    caplog.set_level(logging.DEBUG)

    dd_run_check(new_check())

    assert only_value_and_tags(aggregator, 'can_connect') == (1, FW_A_TAGS)
    assert only_value_and_tags(aggregator, 'api.authentication.status') == (0, FW_A_TAGS)
    assert [(c.type, c.cmd, c.key_sent) for c in fake_panos.calls] == [
        ('keygen', None, False),
        ('op', SYSTEM_INFO_CMD, True),
        ('op', INTERFACE_ALL_CMD, True),
    ]
    assert re.search(rf'pan_firewall {re.escape(FW_A_IP)}: 2 calls in \d+\.\d\ds', caplog.text)


# Transport failures, and HTTP errors whose body is not a PAN-OS response: none of them means the firewall API answered,
# and none of them says anything about the credentials.
@pytest.mark.parametrize('failure', ['timeout', 'refused', 'tls', 'html_502', 'html_403'])
def test_unreachable_on_first_run_reports_disconnected_without_device_id(dd_run_check, aggregator, fake_panos, failure):
    fake_panos.fail(FW_A_IP, failure)
    check = new_check()

    dd_run_check(check)

    assert only_value_and_tags(aggregator, 'can_connect') == (0, BASE_TAGS)
    assert only_value_and_tags(aggregator, 'api.authentication.status') == (0, BASE_TAGS)
    # The next run tries again: the identity is still missing, so system info is due.
    calls_before = len(fake_panos.calls)
    dd_run_check(check)
    assert len(fake_panos.calls) > calls_before


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
    'failure, on, expected',
    [
        pytest.param(None, None, 0, id='ok'),
        pytest.param('http_403', 'keygen', 1, id='keygen-rejected'),
        pytest.param('http_403', 'api', 1, id='key-rejected-again-after-good-keygen'),
    ],
)
def test_authentication_status(dd_run_check, aggregator, fake_panos, failure, on, expected):
    if failure:
        fake_panos.fail(FW_A_IP, failure, on=on)

    dd_run_check(new_check())

    assert aggregator.metrics('pan_firewall.api.authentication.status')[0].value == expected
    # The firewall answered, even if only to refuse the credentials.
    assert aggregator.metrics('pan_firewall.can_connect')[0].value == 1


def test_rejected_keygen_is_tried_once_per_run(dd_run_check, fake_panos):
    fake_panos.fail(FW_A_IP, 'http_403', on='keygen')
    check = new_check()

    dd_run_check(check)
    dd_run_check(check)

    assert [c.type for c in fake_panos.calls] == ['keygen', 'keygen']


def test_nothing_due_repeats_last_status_without_calls(dd_run_check, aggregator, fake_panos):
    check = new_check()
    dd_run_check(check)
    calls = len(fake_panos.calls)
    aggregator.reset()

    dd_run_check(check)

    assert len(fake_panos.calls) == calls
    assert only_value_and_tags(aggregator, 'can_connect') == (1, FW_A_TAGS)
    assert only_value_and_tags(aggregator, 'api.authentication.status') == (0, FW_A_TAGS)


def test_collector_samples_are_submitted_with_global_tags(dd_run_check, aggregator, monkeypatch):
    seen = []

    def collect(ctx):
        seen.append(ctx.identity.serial)
        return [
            Sample('bgp.peer.status', 1, ('peer_ip:10.0.0.1',), 'gauge'),
            Sample('interface.rx.bytes', 42, ('interface:ethernet1/1',), 'monotonic_count'),
            Sample('threat.count', 3, (), 'count'),
        ]

    monkeypatch.setitem(COLLECT_FUNCTIONS, 'bgp', collect)

    dd_run_check(new_check())

    assert seen == [FW_A_SERIAL]
    aggregator.assert_metric(
        'pan_firewall.bgp.peer.status', 1, tags=[*FW_A_TAGS, 'peer_ip:10.0.0.1'], metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric(
        'pan_firewall.interface.rx.bytes',
        42,
        tags=[*FW_A_TAGS, 'interface:ethernet1/1'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_metric('pan_firewall.threat.count', 3, tags=FW_A_TAGS, metric_type=aggregator.COUNT)


def test_disabled_optional_collector_does_not_run(dd_run_check, monkeypatch):
    seen = []
    monkeypatch.setitem(COLLECT_FUNCTIONS, 'ospf', lambda ctx: seen.append('ospf') or [])

    dd_run_check(new_check(make_instance(collect_ospf=False)))

    assert seen == []


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


def test_removed_firewall_poller_is_dropped(dd_run_check):
    check = new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP]))
    dd_run_check(check)
    remaining = [t for t in check._source.list_firewalls() if t.ip == FW_A_IP]
    check._source = type('Source', (), {'list_firewalls': lambda self: remaining})()

    dd_run_check(check)

    assert list(check._pollers) == [FW_A_IP]


def test_timeout_skips_the_remaining_collectors_of_that_firewall_only(
    dd_run_check, aggregator, fake_panos, monkeypatch, caplog
):
    check = new_check(make_instance(firewalls=[FW_A_IP, FW_B_IP]))
    # Caches the identity; no collector is registered yet, so the stubs below are all due on the next run.
    dd_run_check(check)
    dataplane_started = threading.Event()
    bgp_failed = threading.Event()

    def bgp(ctx):
        if ctx.identity.serial == FW_A_SERIAL:
            # dataplane is in flight on the other worker when the call times out.
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
        return [stub_sample('dataplane')]

    register_stubs(monkeypatch, bgp=bgp, dataplane=dataplane)
    fake_panos.fail(FW_A_IP, 'timeout')
    aggregator.reset()
    caplog.clear()

    dd_run_check(check)

    # The collector already in flight finishes; the ones not started yet are skipped.
    assert stub_runs(aggregator) == {(FW_A_IP, 'dataplane'), *((FW_B_IP, name) for name in STUBS)}
    # The timed-out call was the only one this run: the firewall did not answer.
    assert can_connect_by_ip(aggregator) == {FW_A_IP: 0, FW_B_IP: 1}
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [
        f'pan_firewall {FW_A_IP}: bgp timed out after 30s; skipped for this run: interfaces, system_resources'
    ]

    # The skipped collectors stay due; the ones that ran, timed out or not, wait for their interval.
    fake_panos.recover(FW_A_IP)
    aggregator.reset()
    dd_run_check(check)

    assert stub_runs(aggregator) == {(FW_A_IP, 'interfaces'), (FW_A_IP, 'system_resources')}


def test_identity_timeout_skips_every_collector(dd_run_check, aggregator, fake_panos, monkeypatch, caplog):
    dd_run_check(new_check())
    register_stubs(monkeypatch)
    fake_panos.fail(FW_A_IP, 'timeout')
    aggregator.reset()
    caplog.clear()

    # After a restart, the identity comes from the cache and its refresh is the run's first call.
    dd_run_check(new_check())

    assert stub_runs(aggregator) == set()
    assert only_value_and_tags(aggregator, 'can_connect') == (0, FW_A_TAGS)
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [
        f'pan_firewall {FW_A_IP}: identity_metadata timed out after 30s; skipped for this run: {", ".join(STUBS)}'
    ]


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(ValueError('unexpected shape'), id='bug'),
        pytest.param(PanosApiError('400', 'bad command'), id='api-error'),
    ],
)
def test_failing_collector_does_not_stop_the_others(dd_run_check, aggregator, monkeypatch, caplog, error):
    def bgp(ctx):
        raise error

    register_stubs(monkeypatch, bgp=bgp)

    dd_run_check(new_check())

    assert stub_runs(aggregator) == {(FW_A_IP, name) for name in STUBS if name != 'bgp'}
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [f'pan_firewall {FW_A_IP}: collector bgp failed: {error}']


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
        pytest.param({}, (30.0, 30.0), id='default'),
        pytest.param({'timeout': 5}, (5.0, 5.0), id='configured'),
    ],
)
def test_calls_use_the_instance_timeout(dd_run_check, fake_panos, monkeypatch, options, expected):
    timeouts = set()

    def post(self, url, **kwargs):
        timeouts.add(self.options['timeout'])
        return fake_panos.post(url, **kwargs)

    monkeypatch.setattr(RequestsWrapper, 'post', post)

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
