# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from unittest.mock import MagicMock

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.hpe_aruba_edgeconnect import HpeArubaEdgeconnectCheck
from datadog_checks.hpe_aruba_edgeconnect.client import ApplianceClient, OrchestratorClient
from datadog_checks.hpe_aruba_edgeconnect.minute_stats import MinuteStats
from datadog_checks.hpe_aruba_edgeconnect.ndm_models import PAYLOAD_METADATA_BATCH_SIZE

from .common import (
    ALARM_PAYLOAD,
    APPLIANCE_PAYLOAD,
    BASE_DEVICE_TAGS,
    CHECK_MODULE,
    EXPECTED_METRIC_COUNTS,
    EXPECTED_VALUES,
    FIXTURE_DIR,
    NEWEST_TS,
    NS,
    TGZ_BYTES,
    TGZ_DATA,
    _mock_appliance_client,
    _pack_dir_to_tgz_bytes,
    _setup_mocks,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'appliance_ips',
    [
        pytest.param({'include': ['bad-pattern']}, id='include'),
        pytest.param({'exclude': ['bad-pattern']}, id='exclude'),
    ],
)
def test_config_rejects_invalid_appliance_ip_patterns(instance, appliance_ips):
    inst = instance('localhost:8443', appliance_ips=appliance_ips)
    c = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])

    with pytest.raises(Exception, match='Invalid appliance_ips pattern'):
        c.load_configuration_models()


# ---------------------------------------------------------------------------
# Appliance models
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'ips, filter_config, expected_ips',
    [
        pytest.param(
            ['10.0.0.1', '10.0.0.2', '10.0.0.3'],
            {'include': ['10.0.0.1', '10.0.0.3']},
            ['10.0.0.1', '10.0.0.3'],
            id='include',
        ),
        pytest.param(
            ['10.0.0.1', '10.0.0.2', '10.0.0.3'],
            {'exclude': ['10.0.0.2']},
            ['10.0.0.1', '10.0.0.3'],
            id='exclude',
        ),
        pytest.param(
            ['10.0.0.1', '10.0.0.2', '10.0.0.3'],
            {'include': ['10.0.0.1', '10.0.0.2'], 'exclude': ['10.0.0.2']},
            ['10.0.0.1'],
            id='include_and_exclude',
        ),
        pytest.param(
            ['10.0.0.1', '10.0.0.2'],
            None,
            ['10.0.0.1', '10.0.0.2'],
            id='none',
        ),
        pytest.param(
            ['10.0.0.5', '10.0.1.5', '10.0.0.200'],
            {'include': ['10.0.0.0/24']},
            ['10.0.0.5', '10.0.0.200'],
            id='cidr',
        ),
    ],
)
def test_appliances_filter(dd_run_check, aggregator, mocker, instance, ips, filter_config, expected_ips):
    inst = instance('localhost:8443', appliance_ips=filter_config, max_backfill_minutes=10)
    check = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])

    payload = [{**APPLIANCE_PAYLOAD[0], 'ip': ip, 'hostName': f'host-{ip}'} for ip in ips]
    _setup_mocks(mocker, check, payload, appliance_client=_mock_appliance_client(TGZ_DATA))

    dd_run_check(check)

    monitored_ips = sorted(
        tag.split(':', 1)[1]
        for metric in aggregator.metrics(f'{NS}.device.reachability')
        for tag in metric.tags
        if tag.startswith('device_ip:')
    )
    assert monitored_ips == sorted(expected_ips)


@pytest.mark.parametrize(
    'bad_ip',
    [
        pytest.param('appliance.example.com', id='hostname'),
        pytest.param('appliance.example.com:8443', id='host_port'),
        pytest.param('localhost:9999', id='localhost_port'),
        pytest.param('', id='empty'),
    ],
)
def test_appliances_with_non_ip_address_are_skipped(dd_run_check, aggregator, mocker, instance, bad_ip):
    inst = instance('localhost:8443', max_backfill_minutes=10)
    check = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])

    payload = [
        {**APPLIANCE_PAYLOAD[0], 'ip': '10.0.0.1'},
        {**APPLIANCE_PAYLOAD[0], 'ip': bad_ip, 'hostName': 'invalid-appliance'},
    ]
    _setup_mocks(mocker, check, payload, appliance_client=_mock_appliance_client(TGZ_DATA))

    dd_run_check(check)

    monitored_ips = [
        tag.split(':', 1)[1]
        for metric in aggregator.metrics(f'{NS}.device.reachability')
        for tag in metric.tags
        if tag.startswith('device_ip:')
    ]
    assert monitored_ips == ['10.0.0.1']


@pytest.mark.parametrize(
    'value, expected',
    [
        pytest.param('1000Mb/s (auto)', 1_000_000_000, id='1000mbps_auto'),
        pytest.param('25000Mb/s (auto)', 25_000_000_000, id='25000mbps_auto'),
        pytest.param('100Mb/s', 100_000_000, id='100mbps'),
        pytest.param('10Gb/s', 10_000_000_000, id='10gbps'),
        pytest.param('100Kb/s', 100_000, id='100kbps'),
        pytest.param(1000000, 1000000, id='int_passthrough'),
        pytest.param(1000000.0, 1000000.0, id='float_passthrough'),
        pytest.param(None, None, id='none'),
        pytest.param('unknown', None, id='unparseable'),
    ],
)
def test_parse_speed(dd_run_check, aggregator, mocker, check, value, expected):
    client = _mock_appliance_client(TGZ_DATA)
    client.get_network_interfaces.return_value = {'ifInfo': [{'ifname': 'wan0', 'admin': 1, 'oper': 1, 'speed': value}]}
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=client)

    dd_run_check(check)

    if expected is None:
        aggregator.assert_metric(f'{NS}.interface.speed', count=0)
    else:
        aggregator.assert_metric(f'{NS}.interface.speed', value=expected, count=1)


# ---------------------------------------------------------------------------
# Auth, credentials, and login
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'ip, appliance_credentials, expected_username, expected_password',
    [
        pytest.param(
            '192.168.1.5',
            [{'cidr': '192.168.1.0/24', 'username': 'cidr_user', 'password': 'cidr_pass'}],
            'cidr_user',
            'cidr_pass',
            id='cidr_match',
        ),
        pytest.param(
            '10.0.0.1',
            [{'cidr': '192.168.1.0/24', 'username': 'cidr_user', 'password': 'cidr_pass'}],
            'admin',
            'default_pass',
            id='fallback_to_shared',
        ),
        pytest.param(
            '10.0.0.1',
            None,
            'admin',
            'default_pass',
            id='no_overrides',
        ),
        pytest.param(
            '10.0.0.1',
            [
                {'cidr': 'not-a-cidr', 'username': 'bad', 'password': 'bad'},
                {'cidr': '10.0.0.0/24', 'username': 'good', 'password': 'good'},
            ],
            'good',
            'good',
            id='invalid_cidr_skipped',
        ),
        pytest.param(
            '192.168.1.5',
            [{'cidr': '192.168.1.0/24', 'username': 'cidr_user', 'password': ''}],
            'cidr_user',
            '',
            id='empty_password_is_valid',
        ),
        pytest.param(
            '192.168.1.5',
            [
                {'cidr': '192.168.1.0/24', 'username': 'first_user', 'password': 'first_pass'},
                {'cidr': '192.168.0.0/16', 'username': 'second_user', 'password': 'second_pass'},
            ],
            'first_user',
            'first_pass',
            id='first_match_wins',
        ),
    ],
)
def test_resolve_credentials(
    dd_run_check, mocker, instance, ip, appliance_credentials, expected_username, expected_password
):
    inst = instance(
        'localhost:8443',
        orchestrator_username='admin',
        orchestrator_password='default_pass',
        appliance_credentials=appliance_credentials,
    )
    check = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])

    payload = [{**APPLIANCE_PAYLOAD[0], 'ip': ip}]
    _setup_mocks(mocker, check, payload)
    create_client = mocker.patch.object(
        check, '_create_appliance_client', return_value=_mock_appliance_client(TGZ_DATA, app_ip=ip)
    )

    dd_run_check(check)

    create_client.assert_called_once_with(ip, expected_username, expected_password)


@pytest.mark.parametrize(
    'cached_value, latest_timestamp, expected',
    [
        pytest.param(None, 1000, [1000], id='first_run'),
        pytest.param('1000', 1000, [], id='up_to_date'),
        pytest.param('100', 220, [220, 160], id='catchup_newest_first'),
        pytest.param(
            '100',
            100 + 12 * 60,
            [(100 + 12 * 60) - i * 60 for i in range(10)],
            id='catchup_capped_at_max_backfill',
        ),
    ],
)
def test_timestamps_to_fetch(dd_run_check, mocker, check, cached_value, latest_timestamp, expected):
    client = _mock_appliance_client(TGZ_BYTES[0], newest_timestamp=latest_timestamp)
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=client, cached_timestamp=cached_value)
    warning = mocker.patch.object(check.log, 'warning')

    dd_run_check(check)

    fetched = {call.args[0] for call in client.get_minute_stats.call_args_list}
    assert fetched == {f'st2-{ts}.tgz' for ts in expected}

    capped = len(expected) == check.config.max_backfill_minutes and cached_value is not None
    backfill_warned = any('capping backfill' in str(call.args[0]) for call in warning.call_args_list)
    assert backfill_warned is capped


def test_qos_metrics_omit_overlay_tag_without_traffic_class_mapping(dd_run_check, aggregator, mocker, check):
    # No overlay/traffic-class mapping is returned by the orchestrator, so shaper
    # metrics must be emitted without an overlay_name tag.
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=_mock_appliance_client(TGZ_DATA))

    dd_run_check(check)

    qos_metrics = aggregator.metrics(f'{NS}.qos.class.drops')
    assert qos_metrics, 'expected qos.class.drops metrics to be emitted'
    for metric in qos_metrics:
        assert not any(tag.startswith('overlay_name:') for tag in metric.tags)


def test_login_appliance_csrf_token():
    http = MagicMock()
    http.get_cookie.side_effect = lambda name: {'edgeosCsrfToken': 'mytoken'}.get(name)
    http.post.return_value = MagicMock(raise_for_status=MagicMock())
    logger = MagicMock()

    client = ApplianceClient(http, '10.0.0.1', logger)
    client.login('admin', 'pass')

    http.set_header.assert_called_once_with('X-XSRF-TOKEN', 'mytoken')


def test_login_appliance_session_id_fallback():
    http = MagicMock()
    http.get_cookie.side_effect = lambda name: {'vxoaSessionID': 'sess123'}.get(name)
    http.post.return_value = MagicMock(raise_for_status=MagicMock())
    logger = MagicMock()

    client = ApplianceClient(http, '10.0.0.1', logger)
    client.login('admin', 'pass')

    http.set_header.assert_called_once_with('vxoaSessionID', 'sess123')


def test_login_orchestrator_csrf_token():
    http = MagicMock()
    http.get_cookie.side_effect = lambda name: {'orchCsrfToken': 'orchtoken'}.get(name)
    http.post.return_value = MagicMock(raise_for_status=MagicMock())

    client = OrchestratorClient(http, '10.0.0.1')
    client.login('admin', 'pass')

    http.set_header.assert_called_once_with('X-XSRF-TOKEN', 'orchtoken')


@pytest.mark.parametrize(
    'client_factory, login_url',
    [
        pytest.param(
            lambda http: ApplianceClient(http, '10.0.0.1', MagicMock()),
            'https://10.0.0.1/rest/json/login',
            id='appliance',
        ),
        pytest.param(
            lambda http: OrchestratorClient(http, '10.0.0.1'),
            'https://10.0.0.1/gms/rest/authentication/login',
            id='orchestrator',
        ),
    ],
)
def test_request_retries_once_on_401(client_factory, login_url):
    http = MagicMock()
    http.get_cookie.return_value = None
    http.post.return_value = MagicMock(raise_for_status=MagicMock())
    http.get.side_effect = [
        MagicMock(status_code=401, raise_for_status=MagicMock()),
        MagicMock(status_code=200, raise_for_status=MagicMock()),
    ]

    client = client_factory(http)
    client.login('admin', 'pass')
    resp = client._request('get', '/some/path')

    assert resp.status_code == 200
    assert http.get.call_count == 2
    assert http.post.call_count == 2
    assert http.post.call_args_list[0].args[0] == login_url
    assert http.post.call_args_list[1].args[0] == login_url


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def test_empty_minute_stats_files_emit_no_metrics(dd_run_check, aggregator, mocker, check):
    empty_archive = _pack_dir_to_tgz_bytes(
        FIXTURE_DIR / f'st2-{NEWEST_TS}',
        dict.fromkeys(MinuteStats.FILES_NEEDED, ''),
    )
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=_mock_appliance_client(empty_archive))
    # _safe_parse swallows parser exceptions and logs them, so guard against a
    # parser that chokes on empty input rather than returning an empty list.
    log_exception = mocker.patch.object(check.log, 'exception')

    dd_run_check(check)

    log_exception.assert_not_called()
    for metric_name in (
        'interface.bandwidth.tx.count',
        'tunnel.latency',
        'tunnel.internet_breakout.bandwidth.tx.count',
        'qos.class.drops',
        'circuit.sla.latency',
        'nexthop.status',
    ):
        aggregator.assert_metric(f'{NS}.{metric_name}', count=0)
    # The run still completed and emitted endpoint-derived metrics.
    aggregator.assert_metric(f'{NS}.device.reachability', count=1)


# ---------------------------------------------------------------------------
# Check integration
# ---------------------------------------------------------------------------


def test_all_metrics_covered(all_metrics_aggregator):
    all_metrics_aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        check_metric_type=True,
        check_symmetric_inclusion=True,
    )


def test_metric_counts(all_metrics_aggregator):
    for metric_name, expected_count in sorted(EXPECTED_METRIC_COUNTS.items()):
        all_metrics_aggregator.assert_metric(f'{NS}.{metric_name}', count=expected_count)


def test_metric_values(all_metrics_aggregator):
    for metric_name, expected_value, tag_subset in EXPECTED_VALUES:
        full_name = f'{NS}.{metric_name}'
        all_metrics_aggregator.assert_metric(full_name, value=expected_value)
        if tag_subset:
            all_metrics_aggregator.assert_metric_has_tags(full_name, tag_subset)


def test_metrics_carry_base_device_tags(all_metrics_aggregator):
    for metric_name in all_metrics_aggregator.metric_names:
        if not metric_name.startswith(f'{NS}.') or metric_name == f'{NS}.orchestrator.reachability':
            continue
        for stub in all_metrics_aggregator.metrics(metric_name):
            missing = [t for t in BASE_DEVICE_TAGS if t not in stub.tags]
            assert not missing, f'{metric_name} is missing base device tags {missing}; got {stub.tags}'


def test_collection_step_failure_does_not_block_others(dd_run_check, aggregator, mocker, check):
    tgz_bytes = TGZ_BYTES[0]
    client = _mock_appliance_client(tgz_bytes, cpu=42)
    client.get_network_interfaces.side_effect = Exception('network error')
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=client)

    dd_run_check(check)

    aggregator.assert_metric(f'{NS}.device.cpu.usage', count=4)
    aggregator.assert_metric(f'{NS}.device.cpu.usage', value=42 * 0.6, tags=BASE_DEVICE_TAGS + ['cpu_state:user'])
    aggregator.assert_metric(f'{NS}.device.hardware.ok', count=1)


def _events_check(instance):
    inst = instance('localhost:8443', appliance_ips=['10.0.0.1'], max_backfill_minutes=10, collect_events=True)
    return HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])


def test_alarm_events_submitted(dd_run_check, aggregator, mocker, instance):
    check = _events_check(instance)
    client = _mock_appliance_client(TGZ_BYTES[0], alarms=ALARM_PAYLOAD)
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD[:1], appliance_client=client)

    dd_run_check(check)

    aggregator.assert_event(
        'All NTP servers are unreachable',
        count=1,
        exact_match=False,
        alert_type='warning',
        msg_title='[HPE Aruba EdgeConnect] Warning: All NTP servers are unreachable',
        event_type='SW',
        tags=BASE_DEVICE_TAGS
        + [
            'alarm_severity:warning',
            'alarm_source:System',
            'alarm_name:ntpd_server_unreachable',
        ],
    )
    events = aggregator.events
    assert len(events) == 1
    event = events[0]
    assert event['aggregation_key'] == '10.0.0.1:3777'
    assert event['timestamp'] == 1779178081
    assert 'Recommendation:' in event['msg_text']
    check.write_persistent_cache.assert_any_call('last_alarm_ts:10.0.0.1', '1779178081000')


def test_alarm_events_not_collected_when_disabled(dd_run_check, aggregator, mocker, check):
    client = _mock_appliance_client(TGZ_BYTES[0], alarms=ALARM_PAYLOAD)
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD[:1], appliance_client=client)

    dd_run_check(check)

    assert aggregator.events == []


def test_alarm_events_deduped_across_runs(dd_run_check, aggregator, mocker, instance):
    check = _events_check(instance)
    client = _mock_appliance_client(TGZ_BYTES[0], alarms=ALARM_PAYLOAD)
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD[:1], appliance_client=client)

    cache: dict[str, str] = {}
    check.read_persistent_cache.side_effect = lambda key: cache.get(key)
    check.write_persistent_cache.side_effect = lambda key, value: cache.__setitem__(key, value)

    dd_run_check(check)
    assert len([e for e in aggregator.events if 'NTP' in e['msg_text']]) == 1
    assert cache['last_alarm_ts:10.0.0.1'] == '1779178081000'

    aggregator.reset()
    dd_run_check(check)
    assert [e for e in aggregator.events if 'NTP' in e['msg_text']] == []


def test_alarm_events_emitted_when_newer_than_watermark(dd_run_check, aggregator, mocker, instance):
    check = _events_check(instance)
    client = _mock_appliance_client(TGZ_BYTES[0], alarms=ALARM_PAYLOAD)
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD[:1], appliance_client=client)
    # Watermark sits just before the alarm's raised time, so the alarm is still new.
    check.read_persistent_cache.return_value = '1779178080999'

    dd_run_check(check)

    assert len([e for e in aggregator.events if 'NTP' in e['msg_text']]) == 1
    check.write_persistent_cache.assert_any_call('last_alarm_ts:10.0.0.1', '1779178081000')


def test_orchestrator_login_failure_emits_no_metrics(dd_run_check, aggregator, mocker, check):
    orch = _setup_mocks(mocker, check, APPLIANCE_PAYLOAD)
    mocker.patch.object(orch, 'login', side_effect=Exception('bad credentials'))

    with pytest.raises(Exception, match='bad credentials'):
        dd_run_check(check, extract_message=True)

    emitted = [m for m in aggregator.metric_names if m.startswith(f'{NS}.')]
    assert emitted == [f'{NS}.orchestrator.reachability']
    aggregator.assert_metric(f'{NS}.orchestrator.reachability', value=0, count=1)
    assert aggregator.get_event_platform_events('network-devices-metadata') == []
    orch.get_appliances.assert_not_called()
    assert check._orch_client is None


def test_up_to_date_appliance_skips_minute_stats_recording(dd_run_check, aggregator, mocker, check):
    tgz_bytes = TGZ_BYTES[0]
    client = _mock_appliance_client(tgz_bytes)
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=client, cached_timestamp=str(NEWEST_TS))

    dd_run_check(check)

    check.write_persistent_cache.assert_not_called()


def test_ndm_metadata_submitted(dd_run_check, aggregator, mocker, instance):
    inst = instance(
        'localhost:8443',
        appliance_ips=['10.0.0.1'],
        max_backfill_minutes=10,
        send_ndm_metadata=True,
    )
    check = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])

    tgz_bytes = TGZ_BYTES[0]

    client = _mock_appliance_client(tgz_bytes)
    client.get_network_interfaces.return_value = {
        'ifInfo': [
            {'ifname': 'wan0', 'mac': 'aa:bb:cc:dd:ee:ff', 'admin': True, 'oper': True, 'speed': '1000Mb/s (auto)'},
            {'ifname': 'wan0:v100', 'admin': False, 'oper': None},
            {'ifname': 'lan0', 'admin': None, 'oper': False},
        ]
    }

    client.get_interface_labels.return_value = {
        'wan': {'1': 'INET1', '2': 'MPLS1'},
        'lan': {'3': 'Data', '4': 'Voice'},
    }

    _setup_mocks(
        mocker, check, APPLIANCE_PAYLOAD, appliance_client=client, overlay_config=[{'id': 0, 'name': 'business'}]
    )

    dd_run_check(check)

    payloads = [
        e if isinstance(e, dict) else json.loads(e)
        for e in aggregator.get_event_platform_events('network-devices-metadata')
    ]
    assert payloads, 'expected at least one NDM metadata payload to be submitted'

    devices = [d for p in payloads for d in p.get('devices', [])]
    interfaces = [i for p in payloads for i in p.get('interfaces', [])]
    tunnels = [t for p in payloads for t in p.get('tunnels', [])]

    # Devices
    assert len(devices) == 1
    device = devices[0]
    assert device['id'] == 'default:10.0.0.1'
    assert device['ip_address'] == '10.0.0.1'
    assert device['name'] == 'SydneySP01'
    assert device['vendor'] == 'aruba'
    assert device['os_name'] == 'ECOS'
    assert device['serial_number'] == 'SN001'
    assert device['product_name'] == 'EC-V'
    assert device['device_type'] == 'router'
    assert device['version'] == '9.3.1'
    assert device['location'] == 'SYD'
    assert device['site_id'] == 'SYD'
    assert device['site_name'] == 'SYD'
    assert device['status'] == 1
    assert 'device_namespace:default' in device['id_tags']
    assert 'device_ip:10.0.0.1' in device['id_tags']
    assert 'device_hostname:SydneySP01' in device['tags']
    assert 'device_id:default:10.0.0.1' in device['tags']

    # Interfaces: VLAN parsing + admin/oper status conversion
    assert len(interfaces) == 3
    by_name = {i['raw_id']: i for i in interfaces}

    wan0 = by_name['wan0']
    assert wan0['device_id'] == 'default:10.0.0.1'
    assert wan0['id_tags'] == ['interface:wan0']
    assert wan0['mac_address'] == 'aa:bb:cc:dd:ee:ff'
    assert wan0['admin_status'] == 1
    assert wan0['oper_status'] == 1
    assert 'vlan' not in wan0

    vlan_iface = by_name['wan0:v100']
    assert vlan_iface['vlan'] == 100
    assert vlan_iface['admin_status'] == 2
    assert vlan_iface['oper_status'] == 4

    lan0 = by_name['lan0']
    assert 'admin_status' not in lan0
    assert lan0['oper_status'] == 2

    # Tunnels: matching alias with peer in lookup
    by_alias = {t['path_name']: t for t in tunnels}

    with_peer = by_alias['to_SydneySP01_INET1-INET1']
    assert with_peer['src_device_id'] == 'default:10.0.0.1'
    assert with_peer['dst_device_id'] == 'default:10.0.0.1'
    assert with_peer['src_site_id'] == 'SYD'
    assert with_peer['dst_site_id'] == 'SYD'
    assert with_peer['tunnel_color'] == 'INET1-INET1'

    # Tunnels: matching alias with peer resolved from orchestrator appliance list
    ny_peer = by_alias['to_NewYorkSP01_MPLS1-MPLS1']
    assert ny_peer['dst_device_id'] == 'default:10.0.0.2'
    assert ny_peer['dst_site_id'] == 'NYC'
    assert ny_peer['tunnel_color'] == 'MPLS1-MPLS1'
    assert ny_peer['overlay_name'] == 'business'

    # Tunnels: passthrough alias whose middle token is a WAN label resolves to a tunnel_color
    passthrough_wan = by_alias['Passthrough_INET1_wan0']
    assert passthrough_wan['dst_device_id'] == ''
    assert passthrough_wan['dst_site_id'] == ''
    assert passthrough_wan['tunnel_color'] == 'INET1'

    # Tunnels: passthrough alias whose middle token is a LAN label is not treated as a tunnel_color
    non_matching = by_alias['Passthrough_Data_lan0']
    assert non_matching['dst_device_id'] == ''
    assert non_matching['dst_site_id'] == ''
    assert non_matching['tunnel_color'] == ''

    # Payload batching and namespace propagation
    for payload in payloads:
        size = len(payload.get('devices', [])) + len(payload.get('interfaces', [])) + len(payload.get('tunnels', []))
        assert 0 < size <= PAYLOAD_METADATA_BATCH_SIZE
        assert payload['namespace'] == 'default'
        assert payload['collect_timestamp'] is not None


def test_tunnel_metadata_uses_source_minute_stats_timestamp_during_backfill(dd_run_check, aggregator, mocker, instance):
    inst = instance(
        'localhost:8443',
        appliance_ips=['10.0.0.1'],
        max_backfill_minutes=10,
        send_ndm_metadata=True,
    )
    check = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])

    tunnel_stats_ts = NEWEST_TS - 60
    newest_without_tunnels = _pack_dir_to_tgz_bytes(
        FIXTURE_DIR / f'st2-{NEWEST_TS}',
        {'tunnel_v2.txt': ''},
    )
    client = _mock_appliance_client(
        {
            f'st2-{NEWEST_TS}.tgz': newest_without_tunnels,
            f'st2-{tunnel_stats_ts}.tgz': TGZ_DATA[f'st2-{tunnel_stats_ts}.tgz'],
        }
    )
    _setup_mocks(
        mocker,
        check,
        APPLIANCE_PAYLOAD,
        appliance_client=client,
        cached_timestamp=str(tunnel_stats_ts - 60),
    )

    dd_run_check(check)

    payloads = [
        e if isinstance(e, dict) else json.loads(e)
        for e in aggregator.get_event_platform_events('network-devices-metadata')
    ]
    tunnel_payloads = [p for p in payloads if p.get('tunnels')]
    assert tunnel_payloads, 'expected tunnel metadata to be submitted'
    assert {p['collect_timestamp'] for p in tunnel_payloads} == {tunnel_stats_ts}


def test_stale_appliance_clients_cleaned_up(dd_run_check, mocker, instance):
    inst = instance('localhost:8443', appliance_ips=['10.0.0.0/24'], max_backfill_minutes=10)
    check = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])

    def make_client(http, app_ip, log):
        return _mock_appliance_client(TGZ_DATA, app_ip=app_ip)

    mocker.patch(f'{CHECK_MODULE}.ApplianceClient', side_effect=make_client)

    payload_with_extra = APPLIANCE_PAYLOAD[:1] + [
        {**APPLIANCE_PAYLOAD[0], 'ip': '10.0.0.99', 'hostName': 'StaleAppliance'},
    ]
    _setup_mocks(mocker, check, payload_with_extra)
    dd_run_check(check)

    assert set(check._appliance_clients) == {'10.0.0.1', '10.0.0.99'}
    stale_client = check._appliance_clients['10.0.0.99']

    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD[:1])
    dd_run_check(check)

    assert set(check._appliance_clients) == {'10.0.0.1'}
    assert stale_client not in check._appliance_clients.values()
