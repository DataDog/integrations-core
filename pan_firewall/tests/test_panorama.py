# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import logging
from types import SimpleNamespace

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall import panorama as panorama_module
from datadog_checks.pan_firewall.panorama import DiscoveredFirewall, parse_devices, readable_age
from datadog_checks.pan_firewall.xml_utils import parse_response

from .common import CREDENTIALS, FIXTURES, FW_A_IP, FW_A_SERIAL, FW_B_IP, FW_B_SERIAL
from .fake_panos import INVALID_CREDENTIAL
from .helpers import FakeClock, can_connect_by_ip, metrics_by_ip

PANORAMA = 'panorama.example.com'
DISCOVERY_CMD = '<show><devices><connected/></devices></show>'
SYNTHETIC = FIXTURES / 'synthetic' / 'panorama_show_devices_connected.xml'
REAL_CAPTURE = FIXTURES / 'panorama' / 'show_devices_connected.xml'
BAD_KEY_CAPTURE = FIXTURES / 'panorama' / 'op_bad_key.xml'
# The `ip-address` values of the captures. The fake Panorama reports the fake firewalls (FW_A_IP, FW_B_IP) instead.
FW_A_REPORTED, FW_B_REPORTED = '10.60.0.10', '10.60.0.11'
PANORAMA_TAGS = ['device_namespace:default', f'panorama_host:{PANORAMA}', 'team:test']
CACHE_KEY = f'panorama_firewalls:{PANORAMA}'


def make_instance(**options):
    return {
        'panorama_host': PANORAMA,
        'panorama_api_key': 'dummy-api-key',
        'firewall_credentials': copy.deepcopy(CREDENTIALS),
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


def panorama_can_connect(aggregator):
    return [(m.value, sorted(m.tags)) for m in aggregator.metrics('pan_firewall.panorama.can_connect')]


@pytest.mark.parametrize(
    'path, expected',
    [
        # Only the direct children of `devices`: the nested `vsys` and `plugin_versions` entries are not firewalls, the
        # `Total Connected Devices` text is ignored, and a standalone firewall has no `ha` element.
        pytest.param(
            REAL_CAPTURE,
            [
                DiscoveredFirewall(FW_A_SERIAL, 'fw-a', FW_A_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
                DiscoveredFirewall(FW_B_SERIAL, 'fw-b', FW_B_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
            ],
            id='real-capture',
        ),
        pytest.param(
            SYNTHETIC,
            [
                DiscoveredFirewall(FW_A_SERIAL, 'fw-a', FW_A_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
                DiscoveredFirewall(FW_B_SERIAL, 'fw-b', FW_B_REPORTED, 'PA-VM', 'vm', '11.1.13-h12', True),
                DiscoveredFirewall(
                    'SYNTH-DISCONNECTED-0001', 'synth-disconnected', '10.60.0.12', 'PA-VM', 'vm', '11.1.13-h12', False
                ),
                DiscoveredFirewall('SYNTH-NO-IP-0001', 'synth-no-ip', None, 'PA-VM', 'vm', '11.1.13-h12', True),
                DiscoveredFirewall(
                    'SYNTH-UNKNOWN-IP-0001', 'synth-unknown-ip', 'unknown', 'PA-VM', 'vm', '11.1.13-h12', True
                ),
                DiscoveredFirewall('SYNTH-HA-0001', 'synth-ha', None, 'PA-VM', 'vm', '11.1.13-h12', True),
            ],
            id='synthetic-edge-cases',
        ),
    ],
)
def test_parse_devices_reads_every_firewall_entry(path, expected):
    assert parse_devices(parse_response(path.read_bytes())) == expected


def test_discovery_request_is_exactly_the_documented_call_once_per_run(dd_run_check, fake_panos):
    check = new_check()

    dd_run_check(check)
    dd_run_check(check)

    discovery = fake_panos.calls_to(PANORAMA)
    assert [(c.params, c.key_sent) for c in discovery] == [({'type': 'op', 'cmd': DISCOVERY_CMD}, True)] * 2


def test_panorama_key_is_generated_from_username_and_password(dd_run_check, fake_panos):
    check = new_check(panorama_api_key=None, panorama_username='pan-user', panorama_password='pan-pass')

    dd_run_check(check)

    assert [(c.type, c.params.get('user'), c.key_sent) for c in fake_panos.calls_to(PANORAMA)] == [
        ('keygen', 'pan-user', False),
        ('op', None, True),
    ]


def test_panorama_rejecting_the_key_renews_it_once_and_retries_once(dd_run_check, aggregator, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, (200, BAD_KEY_CAPTURE.read_bytes()))

    dd_run_check(new_check(panorama_api_key=None, panorama_username='pan-user', panorama_password='p'))

    assert [c.type for c in fake_panos.calls_to(PANORAMA)] == ['keygen', 'op', 'keygen', 'op']
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]


def test_firewalls_are_polled_at_the_reported_ip_which_is_their_device_ip(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == {FW_A_IP, FW_B_IP}
    can_connect = metrics_by_ip(aggregator, 'can_connect')
    assert {ip: m.value for ip, m in can_connect.items()} == {FW_A_IP: 1, FW_B_IP: 1}
    fw_a_tags = can_connect[FW_A_IP].tags
    assert {f'device_id:{FW_A_SERIAL}', 'device_hostname:fw-a', 'device_model:PA-VM'} <= set(fw_a_tags)


def test_firewall_at_an_unreachable_reported_ip_is_reported_down(dd_run_check, aggregator, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-PRIVATE-0001', 'synth', '10.60.0.40', 'yes')))

    dd_run_check(new_check())

    # Nothing answers at a private IP from here.
    assert polled_hosts(fake_panos) == {'10.60.0.40'}
    assert can_connect_by_ip(aggregator) == {'10.60.0.40': 0}


# TEMPORARY: goes with `LAB_IP_OVERRIDES`.
def test_lab_firewalls_are_polled_at_their_public_ips(dd_run_check, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, (200, REAL_CAPTURE.read_bytes()))

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == {'3.13.247.39', '3.19.110.163'}


@pytest.mark.parametrize(
    'filters, expected',
    [
        pytest.param({'include': ['192.0.2.0/25']}, {FW_A_IP, FW_B_IP}, id='include-cidr'),
        pytest.param({'exclude': ['192.0.2.11']}, {FW_A_IP}, id='exclude'),
        pytest.param({'include': ['192.0.2.0/24'], 'exclude': ['192.0.2.10/32']}, {FW_B_IP}, id='exclude-wins'),
        pytest.param({'include': ['10.60.0.0/24']}, set(), id='include-matches-nothing'),
    ],
)
def test_firewall_ips_filter_the_reported_ip(dd_run_check, fake_panos, filters, expected):
    dd_run_check(new_check(firewall_ips=filters))

    assert polled_hosts(fake_panos) == expected


def test_excluded_firewall_is_never_polled_and_gets_no_can_connect(dd_run_check, aggregator, fake_panos):
    check = new_check(firewall_ips={'exclude': [FW_B_IP]})

    dd_run_check(check)
    dd_run_check(check)

    assert FW_B_IP not in polled_hosts(fake_panos)
    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_IP}
    assert FW_B_IP not in check._pollers


@pytest.mark.parametrize('ip', [None, 'not-an-ip'], ids=['absent', 'invalid'])
def test_entry_without_usable_ip_is_skipped_and_logged(dd_run_check, fake_panos, caplog, ip):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-BAD-IP', 'synth', ip, 'yes')))

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == set()
    assert 'SYNTH-BAD-IP' in caplog.text


def test_renamed_firewall_keeps_its_poller_and_gets_the_new_hostname(dd_run_check, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml((FW_A_SERIAL, 'fw-a', FW_A_IP, 'yes')))
    check = new_check()
    dd_run_check(check)
    poller = check._pollers[FW_A_IP]

    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml((FW_A_SERIAL, 'fw-renamed', FW_A_IP, 'yes')))
    dd_run_check(check)

    assert check._pollers[FW_A_IP] is poller
    assert poller.target.hostname == 'fw-renamed'


def test_firewall_replaced_at_the_same_ip_is_reported_under_its_new_serial(dd_run_check, aggregator, fake_panos):
    check = new_check()
    dd_run_check(check)
    aggregator.reset()
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-RMA-0001', 'fw-a', FW_A_IP, 'yes')))
    # The replacement has not answered yet: the fake would otherwise still reply as the old unit (fw-a's capture).
    fake_panos.fail(FW_A_IP, 'refused')

    dd_run_check(check)

    tags = metrics_by_ip(aggregator, 'can_connect')[FW_A_IP].tags
    assert 'device_id:SYNTH-RMA-0001' in tags
    assert f'device_id:{FW_A_SERIAL}' not in tags


@pytest.mark.parametrize(
    'devices',
    [
        pytest.param(
            devices_xml((FW_A_SERIAL, 'fw-a', FW_A_IP, 'yes'), (FW_B_SERIAL, 'fw-b', FW_B_IP, 'no')),
            id='disconnected',
        ),
        pytest.param(devices_xml((FW_A_SERIAL, 'fw-a', FW_A_IP, 'yes')), id='removed'),
    ],
)
def test_firewall_that_disconnects_or_is_removed_is_no_longer_polled(dd_run_check, aggregator, fake_panos, devices):
    check = new_check()
    dd_run_check(check)
    aggregator.reset()
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices)

    dd_run_check(check)

    # A polled firewall reports `can_connect` on every run, even when nothing is due.
    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_IP}
    assert list(check._pollers) == [FW_A_IP]


def test_credentials_are_matched_on_the_reported_ip(dd_run_check, fake_panos):
    credentials = [
        {'cidr': '192.0.2.10/32', 'username': 'fw-a-user', 'password': 'p'},
        {'cidr': '192.0.2.0/24', 'username': 'subnet-user', 'password': 'p'},
    ]

    dd_run_check(new_check(firewall_credentials=credentials))

    keygen_users = {c.host: c.params['user'] for c in fake_panos.calls if c.type == 'keygen'}
    assert keygen_users == {FW_A_IP: 'fw-a-user', FW_B_IP: 'subnet-user'}


FW_A_ONLY_CREDENTIALS = [{'cidr': '192.0.2.10/32', 'username': 'u', 'password': 'p'}]


def warnings_about(caplog, ip):
    return [r for r in caplog.records if r.levelno == logging.WARNING and ip in r.getMessage()]


def test_firewall_without_matching_credentials_is_skipped_with_a_warning_on_every_run(
    dd_run_check, aggregator, fake_panos, caplog
):
    check = new_check(firewall_credentials=FW_A_ONLY_CREDENTIALS)

    dd_run_check(check)
    dd_run_check(check)

    assert polled_hosts(fake_panos) == {FW_A_IP}
    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_IP}
    assert len(warnings_about(caplog, FW_B_IP)) == 2
    # Also in the Agent status, which drains them after each run.
    assert [w for w in check.get_warnings() if FW_B_IP in w] == [
        f'no entry in `firewall_credentials` matches the firewall {FW_B_SERIAL} at {FW_B_IP}, skipping it'
    ] * 2


def test_missing_credentials_warning_stops_once_the_config_is_fixed(dd_run_check, fake_panos, caplog):
    dd_run_check(new_check(firewall_credentials=FW_A_ONLY_CREDENTIALS))
    caplog.clear()

    # The config with a matching entry, after the Agent reloads it.
    dd_run_check(new_check())

    assert warnings_about(caplog, FW_B_IP) == []
    assert FW_B_IP in polled_hosts(fake_panos)


def test_can_connect_of_an_unreachable_discovered_firewall_carries_its_device_id(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(FW_A_IP, 'refused')

    dd_run_check(new_check())

    tags = metrics_by_ip(aggregator, 'can_connect')[FW_A_IP].tags
    assert metrics_by_ip(aggregator, 'can_connect')[FW_A_IP].value == 0
    # The family comes from discovery too, as the firewall never answered.
    expected = {f'device_id:{FW_A_SERIAL}', f'device_serial:{FW_A_SERIAL}', 'device_hostname:fw-a', 'device_family:vm'}
    assert expected <= set(tags)


def test_panorama_can_connect_is_1_after_a_successful_discovery(dd_run_check, aggregator):
    dd_run_check(new_check())

    assert panorama_can_connect(aggregator) == [(1, sorted(PANORAMA_TAGS))]
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


PASSWORD_LOGIN = {'panorama_api_key': None, 'panorama_username': 'pan-user', 'panorama_password': 'bad'}


@pytest.mark.parametrize(
    'failure, options, calls, error',
    [
        pytest.param(
            (200, b'<response status="error" code="12"><msg><line>Invalid command</line></msg></response>'),
            {},
            ['op', 'op'],
            'PAN-OS API error 12: Invalid command',
            id='api-error',
        ),
        # A static `panorama_api_key` is never renewed: the message says it was rejected.
        pytest.param(
            (200, INVALID_CREDENTIAL),
            {},
            ['op', 'op'],
            f'PAN-OS API error 403: {PANORAMA} rejected the configured API key, which is never renewed',
            id='auth-failure',
        ),
        # The real answer to a keygen with a wrong password: one attempt per run, not a loop within a run.
        pytest.param(
            'capture_bad_password',
            PASSWORD_LOGIN,
            ['keygen', 'keygen'],
            f'PAN-OS API error 403: {PANORAMA} rejected the credentials: API Error: Invalid Credential',
            id='bad-password',
        ),
    ],
)
def test_panorama_can_connect_is_0_when_the_discovery_call_fails(
    dd_run_check, aggregator, fake_panos, caplog, failure, options, calls, error
):
    if isinstance(failure, str):
        fake_panos.fail(PANORAMA, failure, on='keygen')
    else:
        fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, failure)
    check = new_check(**options)

    dd_run_check(check)
    dd_run_check(check)

    assert [c.type for c in fake_panos.calls_to(PANORAMA)] == calls
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))] * 2
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert f'could not get the connected devices from Panorama {PANORAMA}: {error}' in warnings


def test_panorama_that_answers_again_is_reported_and_its_firewalls_polled(dd_run_check, aggregator, fake_panos):
    check = new_check()
    fake_panos.fail(PANORAMA, 'timeout')
    dd_run_check(check)
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    fake_panos.recover(PANORAMA)
    calls = len(fake_panos.calls)
    aggregator.reset()

    # The same check: the timeout of the last run must not make this run's discovery fail fast.
    dd_run_check(check)

    assert panorama_can_connect(aggregator) == [(1, sorted(PANORAMA_TAGS))]
    assert polled_hosts(fake_panos, skip=calls) == {FW_A_IP, FW_B_IP}


def test_unreachable_panorama_keeps_polling_the_last_discovered_firewalls(dd_run_check, aggregator, fake_panos, caplog):
    dd_run_check(new_check())
    fake_panos.fail(PANORAMA, 'refused')
    calls = len(fake_panos.calls)
    aggregator.reset()

    # A new check instance has no list in memory: the persistent cache supplies it, as after an Agent restart.
    dd_run_check(new_check())

    assert polled_hosts(fake_panos, skip=calls) == {FW_A_IP, FW_B_IP}
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
    assert polled_hosts(fake_panos, skip=calls) == {FW_A_IP, FW_B_IP}
    for name, value in (('api.authentication.status', 0), ('can_connect', 1)):
        assert {ip: m.value for ip, m in metrics_by_ip(aggregator, name).items()} == {
            FW_A_IP: value,
            FW_B_IP: value,
        }


def test_unreachable_panorama_without_a_cached_list_polls_nothing_and_does_not_raise(
    dd_run_check, aggregator, fake_panos, caplog
):
    fake_panos.fail(PANORAMA, 'timeout')

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == set()
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert any(r.levelno == logging.WARNING and 'no discovered firewalls' in r.getMessage() for r in caplog.records)


def test_corrupt_cached_list_is_treated_as_no_cached_list(dd_run_check, aggregator, fake_panos, caplog):
    check = new_check()
    dd_run_check(check)
    check.write_persistent_cache(f'panorama_firewalls:{PANORAMA}', '[{"serial": "007955000930601"')
    fake_panos.fail(PANORAMA, 'refused')
    calls = len(fake_panos.calls)
    aggregator.reset()

    # A new check instance reads the list from the persistent cache, as after an Agent restart.
    dd_run_check(new_check())

    assert polled_hosts(fake_panos, skip=calls) == set()
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert any(r.levelno == logging.WARNING and 'no discovered firewalls' in r.getMessage() for r in caplog.records)


def test_cached_list_holds_no_credentials(dd_run_check):
    check = new_check(panorama_api_key='secret-panorama-key')
    dd_run_check(check)

    raw = check.read_persistent_cache(f'panorama_firewalls:{PANORAMA}')
    assert FW_A_SERIAL in raw
    assert 'secret-panorama-key' not in raw
    assert 'dummy-password' not in raw


@pytest.fixture
def wall_clock(monkeypatch) -> FakeClock:
    """The wall clock the Panorama list's `discovered` time comes from."""
    clock = FakeClock(1_800_000_000.0)
    monkeypatch.setattr(panorama_module, 'time', SimpleNamespace(time=clock))
    return clock


def fallback_warnings(caplog):
    return [
        r.getMessage() for r in caplog.records if r.levelno == logging.WARNING and 'last discovery' in r.getMessage()
    ]


def test_fallback_warning_says_how_old_the_list_is_and_its_firewalls_are_polled(
    dd_run_check, fake_panos, caplog, wall_clock
):
    dd_run_check(new_check())
    fake_panos.fail(PANORAMA, 'refused')
    wall_clock.now += 3 * 86400
    calls = len(fake_panos.calls)

    dd_run_check(new_check())

    assert fallback_warnings(caplog) == [
        # The 6 entries of the cached list, of which 2 are connected and have a usable IP.
        f'Panorama {PANORAMA} is unreachable; polling the 6 firewalls of the last discovery, 3 days ago'
    ]
    assert polled_hosts(fake_panos, skip=calls) == {FW_A_IP, FW_B_IP}


def test_successful_discovery_rewrites_the_discovery_time_even_when_the_list_is_unchanged(dd_run_check, wall_clock):
    check = new_check()
    dd_run_check(check)
    first = json.loads(check.read_persistent_cache(CACHE_KEY))
    wall_clock.now += 60

    dd_run_check(check)

    second = json.loads(check.read_persistent_cache(CACHE_KEY))
    assert second['firewalls'] == first['firewalls']
    assert second['discovered'] - first['discovered'] == 60


@pytest.mark.parametrize(
    'cached',
    [
        pytest.param('[{"serial": "007955000930601"}]', id='old-format-bare-list'),
        pytest.param('{"firewalls": []}', id='without-discovered'),
    ],
)
def test_cached_list_in_another_format_is_ignored(dd_run_check, fake_panos, caplog, cached):
    check = new_check()
    dd_run_check(check)
    check.write_persistent_cache(CACHE_KEY, cached)
    fake_panos.fail(PANORAMA, 'refused')
    calls = len(fake_panos.calls)

    dd_run_check(new_check())

    assert polled_hosts(fake_panos, skip=calls) == set()
    assert any(r.levelno == logging.WARNING and 'no discovered firewalls' in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    'seconds, expected',
    [
        pytest.param(-5, '0 seconds', id='clock-went-back'),
        pytest.param(1, '1 second', id='second'),
        pytest.param(59, '59 seconds', id='seconds'),
        pytest.param(60, '1 minute', id='minute'),
        pytest.param(5400, '2 hours', id='hours-rounded'),
        pytest.param(3 * 86400, '3 days', id='days'),
    ],
)
def test_readable_age(seconds, expected):
    assert readable_age(seconds) == expected
