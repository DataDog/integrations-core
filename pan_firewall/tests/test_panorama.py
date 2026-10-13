# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall.panorama import DiscoveredFirewall, parse_devices
from datadog_checks.pan_firewall.xml_utils import parse_response

from .common import CREDENTIALS, FIXTURES

PANORAMA = 'panorama.example.com'
DISCOVERY_CMD = '<show><devices><connected/></devices></show>'
SYNTHETIC = FIXTURES / 'synthetic' / 'panorama_show_devices_connected.xml'
REAL_CAPTURE = FIXTURES / 'panorama' / 'show_devices_connected.xml'
BAD_KEY_CAPTURE = FIXTURES / 'panorama' / 'op_bad_key.xml'
FW_A_SERIAL, FW_B_SERIAL = '007955000930601', '007955000930602'
FW_A_REPORTED, FW_B_REPORTED = '10.60.0.10', '10.60.0.11'
# The fake firewalls (`FIREWALL_SETS`), at documentation IPs: where `firewall_ip_overrides` sends the polling.
FW_A_POLLED, FW_B_POLLED = '192.0.2.10', '192.0.2.11'
OVERRIDES = {FW_A_SERIAL: FW_A_POLLED, FW_B_SERIAL: FW_B_POLLED}
PANORAMA_TAGS = ['device_namespace:default', f'panorama_host:{PANORAMA}', 'team:test']


def make_instance(**options):
    return {
        'panorama_host': PANORAMA,
        'panorama_api_key': 'dummy-api-key',
        'firewall_credentials': copy.deepcopy(CREDENTIALS),
        'firewall_ip_overrides': dict(OVERRIDES),
        'tags': ['team:test'],
        **options,
    }


def new_check(**options):
    return PanFirewallCheck('pan_firewall', {}, [make_instance(**options)])


def devices_xml(*entries):
    """A discovery response with one entry per (serial, hostname, ip-address, connected) tuple."""
    rows = ''.join(
        f'<entry name="{serial}"><serial>{serial}</serial><hostname>{hostname}</hostname>'
        + (f'<ip-address>{ip}</ip-address>' if ip is not None else '')
        + f'<model>PA-VM</model><sw-version>11.1.13-h12</sw-version><connected>{connected}</connected></entry>'
        for serial, hostname, ip, connected in entries
    )
    return (200, f'<response status="success"><result><devices>{rows}</devices></result></response>'.encode())


def polled_hosts(fake_panos, skip=0):
    """The firewall hosts (not Panorama) contacted after the first `skip` calls."""
    return {c.host for c in fake_panos.calls[skip:] if c.host != PANORAMA}


def metrics_by_ip(aggregator, name):
    return {
        next(t.split(':', 1)[1] for t in m.tags if t.startswith('device_ip:')): m
        for m in aggregator.metrics(f'pan_firewall.{name}')
    }


def panorama_can_connect(aggregator):
    return [(m.value, sorted(m.tags)) for m in aggregator.metrics('pan_firewall.panorama.can_connect')]


def test_parse_devices_reads_the_two_firewalls_of_the_real_capture():
    devices = parse_devices(parse_response(REAL_CAPTURE.read_bytes()))

    # Only the direct children of `devices`: the nested `vsys` and `plugin_versions` entries are not firewalls, the
    # `Total Connected Devices` text is ignored, and a standalone firewall has no `ha` element.
    assert devices == [
        DiscoveredFirewall(FW_A_SERIAL, 'fw-a', FW_A_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
        DiscoveredFirewall(FW_B_SERIAL, 'fw-b', FW_B_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
    ]


def test_parse_devices_reads_every_entry_of_the_synthetic_edge_cases():
    devices = parse_devices(parse_response(SYNTHETIC.read_bytes()))

    assert devices == [
        DiscoveredFirewall(FW_A_SERIAL, 'fw-a', FW_A_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
        DiscoveredFirewall(FW_B_SERIAL, 'fw-b', FW_B_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
        DiscoveredFirewall(
            'SYNTH-DISCONNECTED-0001', 'synth-disconnected', '10.60.0.12', 'PA-VM', 'vm', '11.1.13-h12', False
        ),
        DiscoveredFirewall('SYNTH-NO-IP-0001', 'synth-no-ip', None, 'PA-VM', 'vm', '11.1.13-h12', True),
        DiscoveredFirewall('SYNTH-UNKNOWN-IP-0001', 'synth-unknown-ip', 'unknown', 'PA-VM', 'vm', '11.1.13-h12', True),
        DiscoveredFirewall('SYNTH-HA-0001', 'synth-ha', None, 'PA-VM', 'vm', '11.1.13-h12', True),
    ]


def test_discovery_request_is_exactly_the_documented_call(dd_run_check, fake_panos):
    dd_run_check(new_check())

    discovery = fake_panos.calls_to(PANORAMA)
    assert [(c.params, c.key_sent) for c in discovery] == [({'type': 'op', 'cmd': DISCOVERY_CMD}, True)]


def test_discovery_runs_once_per_check_run(dd_run_check, fake_panos):
    check = new_check()

    dd_run_check(check)
    dd_run_check(check)

    assert len(fake_panos.calls_to(PANORAMA)) == 2


def test_panorama_key_is_generated_from_username_and_password(dd_run_check, fake_panos):
    check = new_check(panorama_api_key=None, panorama_username='pan-user', panorama_password='pan-pass')

    dd_run_check(check)

    assert [(c.type, c.params.get('user'), c.key_sent) for c in fake_panos.calls_to(PANORAMA)] == [
        ('keygen', 'pan-user', False),
        ('op', None, True),
    ]


@pytest.mark.parametrize('fixture', [SYNTHETIC, REAL_CAPTURE], ids=['synthetic', 'real-capture'])
def test_overridden_firewalls_are_polled_at_the_overrides_and_keep_the_reported_device_ip(
    dd_run_check, aggregator, fake_panos, fixture
):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, (200, fixture.read_bytes()))

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == {FW_A_POLLED, FW_B_POLLED}
    can_connect = metrics_by_ip(aggregator, 'can_connect')
    assert {ip: m.value for ip, m in can_connect.items()} == {FW_A_REPORTED: 1, FW_B_REPORTED: 1}
    fw_a_tags = can_connect[FW_A_REPORTED].tags
    assert {f'device_id:{FW_A_SERIAL}', 'device_hostname:fw-a', 'device_model:PA-VM'} <= set(fw_a_tags)


def test_panorama_rejecting_the_password_is_reported_after_one_keygen(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(PANORAMA, 'capture_bad_password', on='keygen')

    dd_run_check(new_check(panorama_api_key=None, panorama_username='pan-user', panorama_password='bad'))

    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert [c.type for c in fake_panos.calls_to(PANORAMA)] == ['keygen']


def test_panorama_rejecting_the_key_renews_it_once_and_retries_once(dd_run_check, aggregator, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, (200, BAD_KEY_CAPTURE.read_bytes()))

    dd_run_check(new_check(panorama_api_key=None, panorama_username='pan-user', panorama_password='p'))

    assert [c.type for c in fake_panos.calls_to(PANORAMA)] == ['keygen', 'op', 'keygen', 'op']
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]


def test_firewalls_are_polled_at_the_reported_ip_without_override(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check(firewall_ip_overrides=None))

    # Nothing answers at the private lab IPs from here.
    assert polled_hosts(fake_panos) == {FW_A_REPORTED, FW_B_REPORTED}
    assert {ip: m.value for ip, m in metrics_by_ip(aggregator, 'can_connect').items()} == {
        FW_A_REPORTED: 0,
        FW_B_REPORTED: 0,
    }


@pytest.mark.parametrize(
    'filters, expected',
    [
        pytest.param({'include': ['192.0.2.0/25']}, {FW_A_POLLED, FW_B_POLLED}, id='include-cidr'),
        pytest.param({'include': ['192.0.2.10']}, {FW_A_POLLED}, id='include-ip'),
        pytest.param({'exclude': ['192.0.2.11']}, {FW_A_POLLED}, id='exclude'),
        pytest.param({'include': ['192.0.2.0/24'], 'exclude': ['192.0.2.10/32']}, {FW_B_POLLED}, id='exclude-wins'),
        pytest.param({'include': ['10.60.0.0/24']}, set(), id='filter-applies-to-polled-ip-not-reported'),
    ],
)
def test_firewall_ips_filter_the_polled_ip(dd_run_check, fake_panos, filters, expected):
    dd_run_check(new_check(firewall_ips=filters))

    assert polled_hosts(fake_panos) == expected


@pytest.mark.parametrize('ip', [None, '', 'unknown', 'not-an-ip'], ids=['absent', 'empty', 'unknown', 'invalid'])
def test_entry_without_usable_ip_is_skipped_and_logged(dd_run_check, fake_panos, caplog, ip):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-BAD-IP', 'synth', ip, 'yes')))

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == set()
    assert 'SYNTH-BAD-IP' in caplog.text


def test_override_supplies_the_ip_of_an_entry_without_one(dd_run_check, aggregator, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml((FW_A_SERIAL, 'fw-a', None, 'yes')))

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == {FW_A_POLLED}
    # Panorama reported no IP, so the `device_ip` is the polled override.
    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_POLLED}


def test_firewall_replaced_at_the_same_ip_is_reported_under_its_new_serial(dd_run_check, aggregator, fake_panos):
    check = new_check(firewall_ip_overrides={**OVERRIDES, 'SYNTH-RMA-0001': FW_A_POLLED})
    dd_run_check(check)
    aggregator.reset()
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-RMA-0001', 'fw-a', FW_A_REPORTED, 'yes')))
    # The replacement has not answered yet: the fake would otherwise still reply as the old unit (fw-a's capture).
    fake_panos.fail(FW_A_POLLED, 'refused')

    dd_run_check(check)

    tags = metrics_by_ip(aggregator, 'can_connect')[FW_A_REPORTED].tags
    assert 'device_id:SYNTH-RMA-0001' in tags
    assert f'device_id:{FW_A_SERIAL}' not in tags


def test_disconnected_firewall_is_skipped_with_a_debug_log(dd_run_check, fake_panos, caplog):
    caplog.set_level(logging.DEBUG)
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml((FW_A_SERIAL, 'fw-a', FW_A_REPORTED, 'no')))

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == set()
    assert any(r.levelno == logging.DEBUG and FW_A_SERIAL in r.getMessage() for r in caplog.records)


def test_firewall_that_disconnects_is_no_longer_polled(dd_run_check, aggregator, fake_panos):
    check = new_check()
    dd_run_check(check)
    aggregator.reset()
    fake_panos.answer_op(
        PANORAMA,
        DISCOVERY_CMD,
        devices_xml((FW_A_SERIAL, 'fw-a', FW_A_REPORTED, 'yes'), (FW_B_SERIAL, 'fw-b', FW_B_REPORTED, 'no')),
    )

    dd_run_check(check)

    # A polled firewall reports `can_connect` on every run, even when nothing is due.
    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_REPORTED}


def test_firewall_removed_in_panorama_is_no_longer_polled(dd_run_check, aggregator, fake_panos):
    check = new_check()
    dd_run_check(check)
    aggregator.reset()
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml((FW_A_SERIAL, 'fw-a', FW_A_REPORTED, 'yes')))

    dd_run_check(check)

    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_REPORTED}


def test_credentials_are_matched_on_the_polled_ip(dd_run_check, fake_panos):
    credentials = [
        {'cidr': '192.0.2.0/24', 'username': 'public-user', 'password': 'p'},
        {'cidr': '10.60.0.0/16', 'username': 'private-user', 'password': 'p'},
    ]

    dd_run_check(new_check(firewall_credentials=credentials))

    keygen_users = {c.host: c.params['user'] for c in fake_panos.calls if c.type == 'keygen'}
    assert keygen_users == {FW_A_POLLED: 'public-user', FW_B_POLLED: 'public-user'}


def test_firewall_without_matching_credentials_is_skipped_with_one_warning_per_ip(
    dd_run_check, aggregator, fake_panos, caplog
):
    credentials = [{'cidr': '192.0.2.10/32', 'username': 'u', 'password': 'p'}]
    check = new_check(firewall_credentials=credentials)

    dd_run_check(check)
    dd_run_check(check)

    assert polled_hosts(fake_panos) == {FW_A_POLLED}
    assert FW_B_POLLED not in {c.host for c in fake_panos.calls}
    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_REPORTED}
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and FW_B_POLLED in r.getMessage()]
    assert len(warnings) == 1


def test_can_connect_of_an_unreachable_discovered_firewall_carries_its_device_id(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(FW_A_POLLED, 'refused')

    dd_run_check(new_check())

    tags = metrics_by_ip(aggregator, 'can_connect')[FW_A_REPORTED].tags
    assert metrics_by_ip(aggregator, 'can_connect')[FW_A_REPORTED].value == 0
    # The family comes from discovery too, as the firewall never answered.
    expected = {f'device_id:{FW_A_SERIAL}', f'device_serial:{FW_A_SERIAL}', 'device_hostname:fw-a', 'device_family:vm'}
    assert expected <= set(tags)


def test_panorama_can_connect_is_1_after_a_successful_discovery(dd_run_check, aggregator):
    dd_run_check(new_check())

    assert panorama_can_connect(aggregator) == [(1, sorted(PANORAMA_TAGS))]
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_panorama_can_connect_is_not_sent_in_static_mode(dd_run_check, aggregator):
    instance = {'firewalls': ['192.0.2.10'], 'firewall_credentials': copy.deepcopy(CREDENTIALS)}

    dd_run_check(PanFirewallCheck('pan_firewall', {}, [instance]))

    assert aggregator.metrics('pan_firewall.panorama.can_connect') == []


@pytest.mark.parametrize('failure', ['refused', 'timeout', 'tls', 'http_403', 'code_403', 'html_502'])
def test_panorama_can_connect_is_0_when_the_discovery_call_fails(dd_run_check, aggregator, fake_panos, failure):
    fake_panos.fail(PANORAMA, failure)

    dd_run_check(new_check())

    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]


def test_panorama_can_connect_is_0_when_keygen_fails(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(PANORAMA, 'code_403', on='keygen')

    dd_run_check(new_check(panorama_api_key=None, panorama_username='pan-user', panorama_password='bad'))

    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]


def test_panorama_can_connect_is_0_on_an_api_error(dd_run_check, aggregator, fake_panos, caplog):
    error = b'<response status="error" code="12"><msg><line>Invalid command</line></msg></response>'
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, (200, error))

    dd_run_check(new_check())

    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert 'Invalid command' in caplog.text


def test_panorama_keygen_is_retried_on_every_run_after_bad_credentials(dd_run_check, fake_panos):
    fake_panos.fail(PANORAMA, 'code_403', on='keygen')
    check = new_check(panorama_api_key=None, panorama_username='pan-user', panorama_password='bad')

    dd_run_check(check)
    dd_run_check(check)

    # One attempt per run, not a loop within a run.
    assert [c.type for c in fake_panos.calls_to(PANORAMA)] == ['keygen', 'keygen']


def test_unreachable_panorama_keeps_polling_the_last_discovered_firewalls(dd_run_check, aggregator, fake_panos, caplog):
    dd_run_check(new_check())
    fake_panos.fail(PANORAMA, 'refused')
    calls = len(fake_panos.calls)
    aggregator.reset()

    # A new check instance has no list in memory: the persistent cache supplies it, as after an Agent restart.
    dd_run_check(new_check())

    assert polled_hosts(fake_panos, skip=calls) == {FW_A_POLLED, FW_B_POLLED}
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert any(r.levelno == logging.WARNING and PANORAMA in r.getMessage() for r in caplog.records)


def test_panorama_auth_failure_does_not_change_the_firewalls_auth_status(dd_run_check, aggregator, fake_panos):
    credentials = {'panorama_api_key': None, 'panorama_username': 'pan-user', 'panorama_password': 'p'}
    dd_run_check(new_check(**credentials))
    fake_panos.fail(PANORAMA, 'capture_bad_password', on='keygen')
    calls = len(fake_panos.calls)
    aggregator.reset()

    # A new check instance holds no Panorama key, so it must generate one: the persistent cache supplies the list.
    dd_run_check(new_check(**{**credentials, 'panorama_password': 'bad'}))

    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert [c.type for c in fake_panos.calls[calls:] if c.host == PANORAMA] == ['keygen']
    assert polled_hosts(fake_panos, skip=calls) == {FW_A_POLLED, FW_B_POLLED}
    for name, value in (('api.authentication.status', 0), ('can_connect', 1)):
        assert {ip: m.value for ip, m in metrics_by_ip(aggregator, name).items()} == {
            FW_A_REPORTED: value,
            FW_B_REPORTED: value,
        }


def test_unreachable_panorama_without_a_cached_list_polls_nothing_and_does_not_raise(
    dd_run_check, aggregator, fake_panos, caplog
):
    fake_panos.fail(PANORAMA, 'timeout')

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == set()
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert any(r.levelno == logging.WARNING and 'no discovered firewalls' in r.getMessage() for r in caplog.records)


def test_cached_list_holds_no_credentials(dd_run_check):
    check = new_check(panorama_api_key='secret-panorama-key')
    dd_run_check(check)

    raw = check.read_persistent_cache(f'panorama_firewalls:{PANORAMA}')
    assert FW_A_SERIAL in raw
    assert 'secret-panorama-key' not in raw
    assert 'dummy-password' not in raw
