# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import re

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, Sample

from .common import CREDENTIALS

FW_A_IP = '192.0.2.10'
FW_B_IP = '192.0.2.11'
FW_A_SERIAL = '007955000930601'
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
