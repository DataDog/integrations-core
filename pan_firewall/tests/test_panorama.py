# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import logging
from types import SimpleNamespace

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall import panorama as panorama_module
from datadog_checks.pan_firewall.panorama import DiscoveredFirewall, parse_devices
from datadog_checks.pan_firewall.xml_utils import parse_response

from .common import CREDENTIALS, FIXTURES, FW_A_IP, FW_A_SERIAL, FW_B_IP, FW_B_SERIAL
from .fake_panos import INVALID_CREDENTIAL
from .helpers import FakeClock, can_connect_by_ip, metrics_by_ip

pytestmark = pytest.mark.unit

PANORAMA = 'panorama.example.com'
DISCOVERY_CMD = '<show><devices><connected/></devices></show>'
SYNTHETIC = FIXTURES / 'synthetic' / 'panorama_show_devices_connected.xml'
REAL_CAPTURE = FIXTURES / 'panorama' / 'show_devices_connected.xml'
# The `ip-address` values of the captures. The fake Panorama reports the fake firewalls (FW_A_IP, FW_B_IP) instead.
FW_A_REPORTED, FW_B_REPORTED = '10.20.0.10', '10.20.0.11'
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
                    'SYNTH-DISCONNECTED-0001', 'synth-disconnected', '10.20.0.12', 'PA-VM', 'vm', '11.1.13-h12', False
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


def test_firewalls_are_polled_at_the_reported_ip_which_is_their_device_ip(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == {FW_A_IP, FW_B_IP}
    can_connect = metrics_by_ip(aggregator, 'can_connect')
    assert {ip: m.value for ip, m in can_connect.items()} == {FW_A_IP: 1, FW_B_IP: 1}
    fw_a_tags = can_connect[FW_A_IP].tags
    assert {f'device_id:{FW_A_SERIAL}', 'device_hostname:fw-a', 'device_model:PA-VM'} <= set(fw_a_tags)


def test_firewall_at_an_unreachable_reported_ip_is_reported_down(dd_run_check, aggregator, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-PRIVATE-0001', 'synth', '10.20.0.40', 'yes')))

    dd_run_check(new_check())

    # Nothing answers at a private IP from here.
    assert polled_hosts(fake_panos) == {'10.20.0.40'}
    assert can_connect_by_ip(aggregator) == {'10.20.0.40': 0}


def test_ip_override_polls_the_reported_ip_at_its_mapped_address(dd_run_check, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-PRIVATE-0001', 'synth', '10.20.0.40', 'yes')))

    dd_run_check(new_check(firewall_ip_overrides={'10.20.0.40': FW_A_IP}))

    assert polled_hosts(fake_panos) == {FW_A_IP}


@pytest.mark.parametrize(
    'filters, expected',
    [
        pytest.param({'include': ['192.0.2.0/25']}, {FW_A_IP, FW_B_IP}, id='include-cidr'),
        pytest.param({'exclude': ['192.0.2.11']}, {FW_A_IP}, id='exclude'),
        pytest.param({'include': ['192.0.2.0/24'], 'exclude': ['192.0.2.10/32']}, {FW_B_IP}, id='exclude-wins'),
        pytest.param({'include': ['10.20.0.0/24']}, set(), id='include-matches-nothing'),
    ],
)
def test_firewall_ips_filter_the_reported_ip(dd_run_check, aggregator, fake_panos, filters, expected):
    dd_run_check(new_check(firewall_ips=filters))

    # A filtered-out firewall is not polled and gets no `can_connect`.
    assert polled_hosts(fake_panos) == expected
    assert set(metrics_by_ip(aggregator, 'can_connect')) == expected


@pytest.mark.parametrize('ip', [None, 'not-an-ip'], ids=['absent', 'invalid'])
def test_entry_without_usable_ip_is_skipped_and_logged(dd_run_check, fake_panos, caplog, ip):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml(('SYNTH-BAD-IP', 'synth', ip, 'yes')))

    dd_run_check(new_check())

    assert polled_hosts(fake_panos) == set()
    assert 'SYNTH-BAD-IP' in caplog.text


def test_renamed_firewall_keeps_its_session_and_key(dd_run_check, fake_panos):
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml((FW_A_SERIAL, 'fw-a', FW_A_IP, 'yes')))
    check = new_check()
    dd_run_check(check)

    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices_xml((FW_A_SERIAL, 'fw-renamed', FW_A_IP, 'yes')))
    dd_run_check(check)

    # A new name alone does not make a new poller, which would log in again.
    assert [c.type for c in fake_panos.calls_to(FW_A_IP)].count('keygen') == 1


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
    # `can_connect` cannot tell a released poller from an idle one; this checks the removed firewall's is released.
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


def test_firewall_without_matching_credentials_is_skipped_and_still_reported_for_the_others(
    dd_run_check, aggregator, fake_panos, caplog
):
    dd_run_check(new_check(firewall_credentials=FW_A_ONLY_CREDENTIALS))

    assert polled_hosts(fake_panos) == {FW_A_IP}
    assert set(metrics_by_ip(aggregator, 'can_connect')) == {FW_A_IP}
    assert [w.getMessage() for w in warnings_about(caplog, FW_B_IP)] == [
        f'no entry in `firewall_credentials` matches the firewall {FW_B_SERIAL} at {FW_B_IP}, skipping it'
    ]


@pytest.mark.parametrize(
    'devices, options, marker',
    [
        pytest.param(
            devices_xml((FW_A_SERIAL, 'fw-a', FW_A_IP, 'yes'), ('SYNTH-DUP', 'dup', FW_A_IP, 'yes')),
            {},
            'SYNTH-DUP',
            id='duplicate-ip',
        ),
        pytest.param(devices_xml(('SYNTH-NO-IP', 'no-ip', 'not-an-ip', 'yes')), {}, 'SYNTH-NO-IP', id='no-ip'),
        pytest.param(
            devices_xml((FW_B_SERIAL, 'fw-b', FW_B_IP, 'yes')),
            {'firewall_credentials': FW_A_ONLY_CREDENTIALS},
            FW_B_SERIAL,
            id='no-credentials',
        ),
    ],
)
def test_firewall_warning_is_logged_once_then_at_debug_level(
    dd_run_check, fake_panos, caplog, devices, options, marker
):
    caplog.set_level(logging.DEBUG)
    fake_panos.answer_op(PANORAMA, DISCOVERY_CMD, devices)
    check = new_check(**options)

    dd_run_check(check)
    first_run = len(caplog.records)
    dd_run_check(check)

    about = [(i, r.levelno) for i, r in enumerate(caplog.records) if marker in r.getMessage()]
    # A condition that lasts must not warn on every run (every 60 s), but stays visible at debug level.
    assert [level for i, level in about if i < first_run] == [logging.WARNING]
    assert [level for i, level in about if i >= first_run] == [logging.DEBUG]


def test_can_connect_of_an_unreachable_discovered_firewall_carries_its_device_id(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(FW_A_IP, 'refused')

    dd_run_check(new_check())

    tags = metrics_by_ip(aggregator, 'can_connect')[FW_A_IP].tags
    assert metrics_by_ip(aggregator, 'can_connect')[FW_A_IP].value == 0
    # The family comes from discovery too, as the firewall never answered.
    expected = {f'device_id:{FW_A_SERIAL}', f'device_serial:{FW_A_SERIAL}', 'device_hostname:fw-a', 'device_family:vm'}
    assert expected <= set(tags)


PASSWORD_LOGIN = {'panorama_api_key': None, 'panorama_username': 'pan-user', 'panorama_password': 'bad'}


@pytest.mark.parametrize(
    'failure, options, calls, error',
    [
        pytest.param(
            (200, b'<response status="error" code="12"><msg><line>Invalid command</line></msg></response>'),
            {},
            ['op', 'op'],
            'Invalid command',
            id='api-error',
        ),
        # A static `panorama_api_key` is never renewed: the message says it was rejected.
        pytest.param((200, INVALID_CREDENTIAL), {}, ['op', 'op'], 'rejected the configured API key', id='auth-failure'),
        # The real answer to a keygen with a wrong password: one attempt per run, not a loop within a run.
        pytest.param(
            'capture_bad_password', PASSWORD_LOGIN, ['keygen', 'keygen'], 'rejected the credentials', id='bad-password'
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
    failures = [w.getMessage() for w in warnings_about(caplog, PANORAMA) if 'connected devices' in w.getMessage()]
    assert len(failures) == 2 and all(error in w for w in failures)


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


@pytest.mark.parametrize(
    'cached',
    [
        pytest.param(None, id='no-cached-list'),
        pytest.param('[{"serial": "007900000000001"', id='corrupt'),
        pytest.param('[{"serial": "007900000000001"}]', id='old-format-bare-list'),
        pytest.param('{"firewalls": []}', id='without-discovered'),
    ],
)
def test_unreachable_panorama_without_a_usable_cached_list_polls_nothing_and_does_not_raise(
    dd_run_check, aggregator, fake_panos, caplog, cached
):
    if cached is not None:
        check = new_check()
        dd_run_check(check)
        check.write_persistent_cache(CACHE_KEY, cached)
    fake_panos.fail(PANORAMA, 'refused')
    calls = len(fake_panos.calls)
    aggregator.reset()

    # A new check instance reads the list from the persistent cache, as after an Agent restart.
    dd_run_check(new_check())

    assert polled_hosts(fake_panos, skip=calls) == set()
    assert panorama_can_connect(aggregator) == [(0, sorted(PANORAMA_TAGS))]
    assert any('no discovered firewalls' in w.getMessage() for w in warnings_about(caplog, PANORAMA))


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


def test_fallback_warning_says_how_many_cached_firewalls_are_polled_and_when_they_were_discovered(
    dd_run_check, fake_panos, caplog, wall_clock
):
    fake_panos.answer_op(
        PANORAMA,
        DISCOVERY_CMD,
        devices_xml(
            (FW_A_SERIAL, 'fw-a', FW_A_IP, 'yes'),
            (FW_B_SERIAL, 'fw-b', FW_B_IP, 'yes'),
            ('SYNTH-DISCONNECTED-0001', 'synth-disconnected', '192.0.2.12', 'no'),
        ),
    )
    dd_run_check(new_check())
    fake_panos.fail(PANORAMA, 'refused')
    wall_clock.now += 3 * 86400
    calls = len(fake_panos.calls)

    dd_run_check(new_check())

    (warning,) = fallback_warnings(caplog)
    assert warning == (
        f'Panorama {PANORAMA} is unreachable; polling 2 of the 3 firewalls of the last discovery, '
        'at 2027-01-15 08:00:00 UTC'
    )
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
