# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.hpe_aruba_edgeconnect import HpeArubaEdgeconnectCheck
from datadog_checks.hpe_aruba_edgeconnect.check import _parse_speed
from datadog_checks.hpe_aruba_edgeconnect.client import ApplianceClient, OrchestratorClient
from datadog_checks.hpe_aruba_edgeconnect.metrics_store import AggType, MetricsStore
from datadog_checks.hpe_aruba_edgeconnect.models import Appliance, Appliances, _ip_matches_any
from datadog_checks.hpe_aruba_edgeconnect.ndm_models import PAYLOAD_METADATA_BATCH_SIZE
from datadog_checks.hpe_aruba_edgeconnect.parsers.appperf import AppperfStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.dscp import DscpStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.interface import (
    InterfaceOverlayStats,
    InterfacePeakStats,
    InterfaceStats,
)
from datadog_checks.hpe_aruba_edgeconnect.parsers.minute_stats import MinuteStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.probe import ProbeStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.shaper import ShaperStats
from datadog_checks.hpe_aruba_edgeconnect.parsers.tunnel import (
    JitterStats,
    MosStats,
    TunnelPeakStats,
    TunnelV2Stats,
)

FIXTURE_DIR = Path(__file__).parent / 'fixtures'
TGZ_FILES = sorted(FIXTURE_DIR.glob('*.tgz'))
NEWEST_TS = 100000060
TGZ_DATA = {p.name: p.read_bytes() for p in TGZ_FILES}
CHECK_MODULE = 'datadog_checks.hpe_aruba_edgeconnect.check'
NS = 'hpe_aruba_edgeconnect'
DEVICE_ID = 'default:10.0.0.1'
BASE_TAGS = ['test:tag']

APPLIANCE_PAYLOAD = [
    {
        'hostName': 'SydneySP01',
        'model': 'EC-V',
        'state': 1,
        'systemBandwidth': 300000,
        'site': 'SYD',
        'ip': '10.0.0.1',
        'serial': 'SN001',
        'mode': 'router',
        'softwareVersion': '9.3.1',
    },
    {
        'hostName': 'NewYorkSP01',
        'model': 'EC-V',
        'state': 1,
        'systemBandwidth': 300000,
        'site': 'NYC',
        'ip': '10.0.0.2',
        'serial': 'SN002',
        'mode': 'router',
        'softwareVersion': '9.3.1',
    },
    {
        'hostName': 'SanFranSP02',
        'model': 'EC-V',
        'state': 1,
        'systemBandwidth': 300000,
        'site': 'SFO',
        'ip': '10.0.0.3',
        'serial': 'SN003',
        'mode': 'router',
        'softwareVersion': '9.3.1',
    },
]

SYSTEM_INFO_PAYLOAD = {
    'hostName': 'SanFranSP01',
    'applianceid': 193645,
    'model': 'EC-V 209005002001 Rev 102786',
    'modelShort': 'EC-V',
    'platform': 'VMware',
    'status': 'Normal',
    'uptime': 816745152,
    'uptimeString': '9d 10h 52m 25s',
    'datetime': '2026/05/08 07:53:33 Etc/UTC',
    'timezone': 'Etc/UTC',
    'gmtOffset': 0,
    'release': 'ECOS 9.5.2.1_102786',
    'releaseWithoutPrefix': '9.5.2.1_102786',
    'serial': '00-00-00-02-F4-6D',
    'uuid': '3dbcbf55-33e0-418f-b98c-3626f98cb0da',
    'nepk': '',
    'portalObjectId': '69f11f4fa66feceed31bde83',
    'deploymentMode': 'router',
    'inlineRouter': True,
    'licenseRequired': False,
    'isLicenseInstalled': False,
    'licenseExpiryDate': '',
    'licenseExpirationDaysLeft': 1.7976931348623157e308,
    'hasUnsavedChanges': False,
    'rebootRequired': False,
    'biosVersion': '6.00',
    'alarmSummary': {
        'num_cleared': 0,
        'num_critical': 0,
        'num_equipment_outstanding': 0,
        'num_major': 0,
        'num_minor': 0,
        'num_outstanding': 1,
        'num_raise_ignore': 0,
        'num_software_outstanding': 1,
        'num_tca_outstanding': 0,
        'num_traffic_class_outstanding': 0,
        'num_tunnel_outstanding': 0,
        'num_warning': 1,
    },
    'suricata': '6.0.10',
    'ccStatus': False,
    'sku': 'N/A',
}

EXPECTED_METRIC_COUNTS = {
    # Device health (orchestrator + appliance client)
    'device.reachability': 1,
    'device.uptime': 1,
    'device.cpu.usage': 5,
    'device.memory.usage': 5,
    'device.disk.usage': 10,
    'device.hardware.ok': 1,
    # Interface status/speed (from mock — 1 interface)
    'interface.status': 1,
    'interface.speed': 1,
    # Interface bandwidth (5 ifname × traffic-type combos across both fixtures)
    'interface.bandwidth.tx.count': 5,
    'interface.bandwidth.rx.count': 5,
    'interface.bandwidth.tx.rate': 5,
    'interface.bandwidth.rx.rate': 5,
    'interface.bandwidth.tx.max': 5,
    'interface.bandwidth.rx.max': 5,
    # Interface drops (5 combos)
    'interface.drops.bytes.tx.count': 5,
    'interface.drops.bytes.rx.count': 5,
    'interface.drops.bytes.tx.rate': 5,
    'interface.drops.bytes.rx.rate': 5,
    'interface.drops.bytes.tx.max': 5,
    'interface.drops.bytes.rx.max': 5,
    'interface.drops.packets.tx.count': 5,
    'interface.drops.packets.rx.count': 5,
    'interface.drops.packets.tx.rate': 5,
    'interface.drops.packets.rx.rate': 5,
    'interface.drops.packets.tx.max': 5,
    'interface.drops.packets.rx.max': 5,
    # Interface utilization (5 ifname × traffic-type combos)
    'interface.utilization.tx.avg': 5,
    'interface.utilization.rx.avg': 5,
    'interface.utilization.tx.max': 5,
    'interface.utilization.rx.max': 5,
    # Tunnel throughput (33 tunnels × 2 sides)
    'tunnel.throughput.tx.bps.count': 66,
    'tunnel.throughput.rx.bps.count': 66,
    'tunnel.throughput.tx.bps.rate': 66,
    'tunnel.throughput.rx.bps.rate': 66,
    'tunnel.throughput.tx.pps.count': 66,
    'tunnel.throughput.rx.pps.count': 66,
    'tunnel.throughput.tx.pps.rate': 66,
    'tunnel.throughput.rx.pps.rate': 66,
    'tunnel.throughput.tx.bps.max': 66,
    'tunnel.throughput.rx.bps.max': 66,
    'tunnel.throughput.tx.pps.max': 66,
    'tunnel.throughput.rx.pps.max': 66,
    # Tunnel latency (33 tunnels)
    'tunnel.latency': 33,
    'tunnel.latency.min': 33,
    'tunnel.latency.max': 33,
    # Tunnel loss (33 tunnels × 2 FEC types)
    'tunnel.loss': 66,
    # Tunnel jitter (31 tunnels in jitter.csv)
    'tunnel.jitter': 31,
    'tunnel.jitter.max': 31,
    # Tunnel MOS (31 tunnels × 2 FEC types)
    'tunnel.qoe.mos': 62,
    'tunnel.qoe.mos.min': 62,
    # Tunnel availability (31 entries)
    'tunnel.status': 31,
    # Internet breakout (2 overlay interfaces)
    'tunnel.internet_breakout.bandwidth.tx.count': 2,
    'tunnel.internet_breakout.bandwidth.rx.count': 2,
    'tunnel.internet_breakout.bandwidth.tx.rate': 2,
    'tunnel.internet_breakout.bandwidth.rx.rate': 2,
    'tunnel.internet_breakout.bandwidth.tx.max': 2,
    'tunnel.internet_breakout.bandwidth.rx.max': 2,
    # SLA probes (4 targets)
    'circuit.sla.latency': 4,
    'circuit.sla.loss': 4,
    'circuit.sla.jitter': 4,
    # Nexthop status (4 targets × 2 status types)
    'nexthop.status': 8,
    # QoS shaper (2 traffic classes × 2 directions × 2 drop types)
    'qos.class.drops': 8,
    'qos.class.drop.percentage': 4,
    # DSCP bandwidth (2 DSCP classes × 2 sides × up to 2 traffic types)
    'qos.class.bandwidth.tx.count': 6,
    'qos.class.bandwidth.rx.count': 6,
    'qos.class.bandwidth.tx.rate': 6,
    'qos.class.bandwidth.rx.rate': 6,
    'qos.class.bandwidth.tx.max': 6,
    'qos.class.bandwidth.rx.max': 6,
}

BASE_DEVICE_TAGS = [
    'device_namespace:default',
    'device_ip:10.0.0.1',
    'device_model:EC-V',
    'device_hostname:SydneySP01',
    'softwareVersion:9.3.1',
    'device_vendor:aruba',
    'site_id:SYD',
    'site_name:SYD',
    'dd.internal.resource:ndm_device:default:10.0.0.1',
    'dd.internal.resource:ndm_device_user_tags:default:10.0.0.1',
]

EXPECTED_VALUES = [
    # --- device health ---
    ('device.reachability', 1, []),
    ('device.uptime', 816745.152, []),
    ('device.cpu.usage', 30.0, ['cpu_state:user']),
    ('device.cpu.usage', 15.0, ['cpu_state:system']),
    ('device.cpu.usage', 3.0, ['cpu_state:irq']),
    ('device.cpu.usage', 2.0, ['cpu_state:nice']),
    ('device.cpu.usage', 50.0, ['cpu_state:idle']),
    ('device.memory.usage', 3945080, ['memory_type:total']),
    ('device.memory.usage', 770848, ['memory_type:free']),
    ('device.memory.usage', 3174232, ['memory_type:used']),
    ('device.memory.usage', 2516, ['memory_type:buffers']),
    ('device.memory.usage', 729568, ['memory_type:cached']),
    ('device.disk.usage', 1193348 * 1024, ['mount:/', 'disk_type:used']),
    ('device.disk.usage', 4619060 * 1024, ['mount:/', 'disk_type:free']),
    ('device.disk.usage', 4328968 * 1024, ['mount:/var', 'disk_type:used']),
    ('device.disk.usage', 35553256 * 1024, ['mount:/var', 'disk_type:free']),
    ('device.hardware.ok', 0, []),
    # --- interface status / speed (from mock) ---
    ('interface.status', 1, ['interface_name:wan0', 'admin_status:up', 'oper_status:up']),
    ('interface.speed', 1000000000, ['interface_name:wan0']),
    # --- interface bandwidth: wan0 pass-through-unshaped (aggregated across two minutes) ---
    ('interface.bandwidth.tx.count', 158508, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.tx.rate', 1320.9, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.count', 82824, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    # --- interface peak: wan0 pass-through-unshaped ---
    ('interface.bandwidth.tx.max', 1332, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.max', 696, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    # --- tunnel throughput: pass-through-unshaped wan (aggregated across two minutes) ---
    ('tunnel.throughput.tx.bps.count', 76320, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    ('tunnel.throughput.tx.bps.rate', 5088.0, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    ('tunnel.throughput.rx.bps.count', 83984, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    # --- tunnel latency: tunnel_12 → to_NewYorkSP01_MPLS1-MPLS1 ---
    ('tunnel.latency', 1.4, ['tunnel_name:to_NewYorkSP01_MPLS1-MPLS1']),
    ('tunnel.latency.min', 1.38, ['tunnel_name:to_NewYorkSP01_MPLS1-MPLS1']),
    # --- tunnel peak: pass-through-unshaped wan ---
    ('tunnel.throughput.tx.bps.max', 1272, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    ('tunnel.throughput.rx.bps.max', 1160, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    # --- tunnel jitter: bondedTunnel_16 ---
    ('tunnel.jitter', 350, ['tunnel_name:bondedTunnel_16']),
    ('tunnel.jitter.max', 6, ['tunnel_name:bondedTunnel_16']),
    # --- tunnel MOS: tunnel_12 (mos_postfec=4.0) ---
    ('tunnel.qoe.mos', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    ('tunnel.qoe.mos.min', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    # --- tunnel availability: pass-through-unshaped (seconds_down=0) ---
    ('tunnel.status', 0, ['tunnel_name:pass-through-unshaped']),
    # --- internet breakout: wan0 (aggregated across two minutes) ---
    ('tunnel.internet_breakout.bandwidth.tx.count', 76012, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.tx.rate', 316.71666666666664, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.rx.max', 100000, ['interface_name:wan0']),
    # --- DSCP: be / pass-through-unshaped wan (aggregated across two minutes) ---
    ('qos.class.bandwidth.tx.count', 75684, ['dscp:be', 'side:wan']),
    ('qos.class.bandwidth.tx.rate', 630.7, ['dscp:be', 'side:wan']),
    # --- DSCP peak: be / pass-through-unshaped wan ---
    ('qos.class.bandwidth.tx.max', 636, ['dscp:be', 'side:wan']),
    # --- shaper: traffic_class=2 -> overlay BulkData, qos_drops=0 ---
    ('qos.class.drops', 0, ['overlay_name:BulkData', 'drop_type:qos']),
    ('qos.class.drop.percentage', 0, ['overlay_name:BulkData']),
    # --- probe: om_passThrough_9 (averaged across two minutes) ---
    ('circuit.sla.latency', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.loss', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.jitter', 59.5, ['probe_name:om_passThrough_9']),
    # --- nexthop: om_passThrough_6 admin=60, oper=0 ---
    ('nexthop.status', 60, ['probe_name:om_passThrough_6', 'status_type:admin']),
    ('nexthop.status', 0, ['probe_name:om_passThrough_6', 'status_type:oper']),
]

PARSER_CASES = [
    ("interfaces", "interface.csv"),
    ("interface_peaks", "interface_peak.csv"),
    ("tunnels", "tunnel_v2.txt"),
    ("tunnel_peaks", "tunnel_peak.csv"),
    ("jitter", "jitter.csv"),
    ("mos", "mos.csv"),
    ("dscp", "dscp.csv"),
    ("dscp_peaks", "dscp_peak.csv"),
    ("tunnel_availability", "tunnel_availability_v2.txt"),
    ("interface_overlays", "interface_overlay.csv"),
    ("probes", "probe_v2.txt"),
    ("shaper", "shaper.csv"),
    ("appperf", "appperf_v2.txt"),
]

EMPTY_PARSE_CASES = [
    InterfaceStats,
    TunnelV2Stats,
    JitterStats,
    MosStats,
    DscpStats,
    ProbeStats,
    ShaperStats,
    AppperfStats,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_appliance(ip='10.0.0.1', **overrides):
    data = {
        'ip': ip,
        'hostName': 'test',
        'state': 1,
        'model': 'EC-V',
        'serial': 'SN123',
        'mode': 'router',
        'softwareVersion': '9.3',
        'site': 'NYC',
        **overrides,
    }
    return Appliance(data)


def _mock_orch_client(appliance_payload, overlay_map=None, traffic_class_map=None):
    client = MagicMock()
    client.get_appliances.return_value = appliance_payload
    client.get_overlay_config.return_value = (overlay_map or {}, traffic_class_map or {})
    return client


MEMORY_PAYLOAD = {
    'total': 3945080,
    'free': 770848,
    'buffers': 2516,
    'cached': 729568,
    'used': 3174232,
}

DISK_PAYLOAD = {
    '/dev': {'1k-blocks': 1965848, 'used': 0, 'available': 1965848, 'usedpercent': 0, 'filesystem': 'none'},
    '/': {
        '1k-blocks': 6126976,
        'used': 1193348,
        'available': 4619060,
        'usedpercent': 21,
        'filesystem': '/dev/disk/by-label/ROOT_1',
    },
    '/var': {
        '1k-blocks': 42030588,
        'used': 4328968,
        'available': 35553256,
        'usedpercent': 11,
        'filesystem': '/root/dev/disk/by-label/VAR',
    },
    '/boot': {'1k-blocks': 999288, 'used': 31676, 'available': 915188, 'usedpercent': 4, 'filesystem': '/dev/sda5'},
    '/bootmgr': {'1k-blocks': 999320, 'used': 3268, 'available': 943624, 'usedpercent': 1, 'filesystem': '/dev/sda1'},
    '/config': {'1k-blocks': 1015700, 'used': 1632, 'available': 961640, 'usedpercent': 1, 'filesystem': '/dev/sda3'},
    '/run': {'1k-blocks': 1972540, 'used': 4776, 'available': 1967764, 'usedpercent': 1, 'filesystem': 'tmpfs'},
    '/var/volatile': {
        '1k-blocks': 1972540,
        'used': 2384,
        'available': 1970156,
        'usedpercent': 1,
        'filesystem': 'tmpfs',
    },
}


def _build_cpu_payload(usage):
    idle = 100 - usage
    return {
        'latestTimestamp': NEWEST_TS,
        'data': [
            {
                str(NEWEST_TS): [
                    {
                        'cpu_number': 'ALL',
                        'pIdle': str(idle),
                        'pUser': str(usage * 0.6),
                        'pSys': str(usage * 0.3),
                        'pIRQ': str(usage * 0.06),
                        'pNice': str(usage * 0.04),
                    },
                ],
            },
        ],
    }


def _mock_appliance_client(
    tgz_data, newest_timestamp=NEWEST_TS, cpu=50, mem=None, disk=None, alarms=None, system_info=None
):
    client = MagicMock()
    client.get_newest_timestamp.return_value = newest_timestamp
    if isinstance(tgz_data, dict):
        client.get_minute_stats.side_effect = lambda fname: tgz_data[fname]
    else:
        client.get_minute_stats.return_value = tgz_data
    client.get_network_interfaces.return_value = {
        'ifInfo': [{'ifname': 'wan0', 'admin': 1, 'oper': 1, 'speed': '1000Mb/s (auto)'}]
    }
    client.get_cpu_stats.return_value = _build_cpu_payload(cpu)
    client.get_memory_stats.return_value = mem if mem is not None else MEMORY_PAYLOAD
    client.get_disk_usage.return_value = disk if disk is not None else DISK_PAYLOAD
    client.get_alarms.return_value = (
        alarms if alarms is not None else {'outstanding': [{'type': 'HW'}, {'type': 'TUNNEL'}]}
    )
    client.get_system_info.return_value = system_info if system_info is not None else SYSTEM_INFO_PAYLOAD
    client.app_ip = '10.0.0.1'
    return client


def _setup_mocks(
    mocker,
    check,
    appliance_payload,
    tgz_bytes=None,
    appliance_client=None,
    overlay_map=None,
    traffic_class_map=None,
    cached_timestamp=None,
):
    orch = _mock_orch_client(appliance_payload, overlay_map, traffic_class_map)
    mocker.patch(f'{CHECK_MODULE}.OrchestratorClient', return_value=orch)

    if appliance_client is not None:
        mocker.patch.object(check, '_create_appliance_client', return_value=appliance_client)
    elif tgz_bytes is not None:
        mocker.patch.object(check, '_create_appliance_client', return_value=_mock_appliance_client(tgz_bytes))

    mocker.patch.object(check, 'read_persistent_cache', return_value=cached_timestamp)
    mocker.patch.object(check, 'write_persistent_cache')
    return orch


def _call_record(row, store, tags):
    if isinstance(row, (InterfaceStats, InterfaceOverlayStats)):
        row.record(store, tags, DEVICE_ID)
    elif isinstance(row, InterfacePeakStats):
        row.record(store, tags, DEVICE_ID, (1000.0, 1000.0))
    elif isinstance(row, TunnelPeakStats):
        row.record(store, tags, [])
    else:
        row.record(store, tags)


def _parse(parser_cls, content, logger):
    try:
        return list(parser_cls.parse(content, logger))
    except TypeError:
        return list(parser_cls.parse(content))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def check(instance):
    inst = instance('localhost:8443', appliance_ips=['10.0.0.1'], max_backfill_minutes=10)
    c = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])
    c.load_configuration_models()
    return c


@pytest.fixture
def all_metrics_aggregator(dd_run_check, aggregator, mocker, check):
    client = _mock_appliance_client(TGZ_DATA)
    _setup_mocks(
        mocker,
        check,
        APPLIANCE_PAYLOAD,
        appliance_client=client,
        cached_timestamp='99999940',
        overlay_map={'0': 'business'},
        traffic_class_map={'2': 'BulkData', '4': 'RealTime'},
    )
    dd_run_check(check)
    return aggregator


@pytest.fixture(scope='module', params=[p.name for p in TGZ_FILES], ids=[p.stem for p in TGZ_FILES])
def minute_stats(request, logger):
    path = FIXTURE_DIR / request.param
    return MinuteStats(path.read_bytes(), appliance_ip='10.0.0.1', timestamp=123456789, logger=logger)


# ---------------------------------------------------------------------------
# MetricsStore aggregation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agg_type, records, expected_value, expected_tags",
    [
        pytest.param(AggType.SUM, [(10, ["tag:a"]), (20, ["tag:a"]), (30, ["tag:a"])], 60, ["tag:a"], id="sum"),
        pytest.param(AggType.AVG, [(10, ["tag:a"]), (20, ["tag:a"]), (30, ["tag:a"])], 20.0, ["tag:a"], id="avg"),
        pytest.param(AggType.MAX, [(10, ["tag:a"]), (30, ["tag:a"]), (20, ["tag:a"])], 30, ["tag:a"], id="max"),
        pytest.param(AggType.MIN, [(30, ["tag:a"]), (10, ["tag:a"]), (20, ["tag:a"])], 10, ["tag:a"], id="min"),
        pytest.param(AggType.LAST, [(10, ["tag:a"]), (20, ["tag:a"]), (30, ["tag:a"])], 30, ["tag:a"], id="last"),
        pytest.param(
            AggType.SUM,
            [(10, ["b:2", "a:1"]), (20, ["a:1", "b:2"])],
            30,
            ["a:1", "b:2"],
            id="tag_dedup_and_sort",
        ),
        pytest.param(AggType.SUM, [(42, ["tag:x"])], 42, ["tag:x"], id="single_value_sum"),
        pytest.param(AggType.AVG, [(42, ["tag:x"])], 42, ["tag:x"], id="single_value_avg"),
        pytest.param(AggType.MAX, [(42, ["tag:x"])], 42, ["tag:x"], id="single_value_max"),
        pytest.param(AggType.MIN, [(42, ["tag:x"])], 42, ["tag:x"], id="single_value_min"),
        pytest.param(AggType.LAST, [(42, ["tag:x"])], 42, ["tag:x"], id="single_value_last"),
        pytest.param(
            AggType.SUM,
            [(5.5, ["env:prod", "host:abc"])],
            5.5,
            ["env:prod", "host:abc"],
            id="float_value_with_multiple_tags",
        ),
    ],
)
def test_aggregation(agg_type, records, expected_value, expected_tags):
    store = MetricsStore()
    for value, tags in records:
        store.record("test.metric", value, tags, agg_type)

    mock_check = MagicMock()
    store.flush(mock_check)

    mock_check.gauge.assert_called_once_with("test.metric", expected_value, tags=expected_tags)


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
def test_appliances_filter(ips, filter_config, expected_ips):
    appliances = Appliances([_make_appliance(ip=ip) for ip in ips])
    appliances.filter(filter_config)
    assert [a.ip for a in appliances] == expected_ips


@pytest.mark.parametrize(
    'ip, patterns, expected',
    [
        pytest.param('10.0.0.1', ['10.0.0.1'], True, id='exact'),
        pytest.param('10.0.0.50', ['10.0.0.0/24'], True, id='cidr'),
        pytest.param('10.0.0.1', ['10.0.0.2', '192.168.0.0/16'], False, id='no_match'),
        pytest.param('not-an-ip', ['10.0.0.0/24'], False, id='invalid_ip'),
        pytest.param('10.0.0.1', ['bad-pattern', '10.0.0.1'], True, id='invalid_pattern'),
        pytest.param('10.0.0.1', ['bad-pattern'], False, id='only_invalid_pattern'),
    ],
)
def test_ip_matches_any(ip, patterns, expected):
    assert _ip_matches_any(ip, patterns) is expected


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
def test_parse_speed(value, expected):
    assert _parse_speed(value) == expected


# ---------------------------------------------------------------------------
# Auth, credentials, and login
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'ip, overrides, expected_username, expected_password',
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
    ],
)
def test_resolve_credentials(ip, overrides, expected_username, expected_password):
    a = _make_appliance(ip=ip)
    appliances = Appliances([a])
    appliances.resolve_credentials('admin', 'default_pass', overrides)

    assert a.username == expected_username
    assert a.password == expected_password


@pytest.mark.parametrize(
    'cached_value, latest_timestamp, expected',
    [
        pytest.param(None, 1000, [1000], id='first_run'),
        pytest.param('1000', 1000, [], id='up_to_date'),
        pytest.param('100', 220, [220, 160], id='catchup_newest_first'),
    ],
)
def test_timestamps_to_fetch(check, mocker, cached_value, latest_timestamp, expected):
    mocker.patch.object(check, 'read_persistent_cache', return_value=cached_value)
    result = check._timestamps_to_fetch('10.0.0.1', latest_timestamp)
    assert result == expected


def test_get_overlay_config_returns_overlay_and_traffic_class_maps():
    http = MagicMock()
    http.get.return_value = MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(
            return_value=[
                {'id': 1, 'name': 'RealTime', 'trafficClass': '1'},
                {'id': 2, 'name': 'BulkData', 'trafficClass': '2'},
                {'id': 3, 'name': 'NoTrafficClass'},
                {'id': 4},
                'not-a-dict',
            ]
        ),
    )

    client = OrchestratorClient(http, '10.0.0.1')
    overlay_map, traffic_class_map = client.get_overlay_config()

    assert overlay_map == {'1': 'RealTime', '2': 'BulkData', '3': 'NoTrafficClass', '4': '4'}
    assert traffic_class_map == {'1': 'RealTime', '2': 'BulkData'}


def test_shaper_record_uses_overlay_name_when_mapped():
    store = MetricsStore()
    row = ShaperStats({'traffic_class': '1', 'direction': '0', 'qos_drops': '5', 'other_drops': '0'})
    row.record(store, [], traffic_class_map={'1': 'RealTime'})

    mock_check = MagicMock()
    store.flush(mock_check)

    args, kwargs = mock_check.gauge.call_args_list[0]
    assert 'overlay_name:RealTime' in kwargs['tags']
    assert 'overlay_name:1' not in kwargs['tags']


def test_shaper_record_falls_back_to_raw_id_and_warns_when_not_mapped():
    store = MetricsStore()
    row = ShaperStats({'traffic_class': '7', 'direction': '0', 'qos_drops': '0', 'other_drops': '0'})
    logger = MagicMock()
    row.record(store, [], traffic_class_map={'1': 'RealTime'}, logger=logger)

    mock_check = MagicMock()
    store.flush(mock_check)

    args, kwargs = mock_check.gauge.call_args_list[0]
    assert 'overlay_name:7' in kwargs['tags']
    logger.warning.assert_called_once()
    assert '7' in logger.warning.call_args.args


def test_shaper_record_does_not_warn_when_no_logger_provided():
    store = MetricsStore()
    row = ShaperStats({'traffic_class': '7', 'direction': '0', 'qos_drops': '0', 'other_drops': '0'})
    row.record(store, [], traffic_class_map={})


def test_login_appliance_csrf_token():
    http = MagicMock()
    http.session.cookies = {'edgeosCsrfToken': 'mytoken'}
    http.session.headers = {}
    http.post.return_value = MagicMock(raise_for_status=MagicMock())
    logger = MagicMock()

    client = ApplianceClient(http, '10.0.0.1', logger)
    client.login('admin', 'pass')

    assert http.session.headers.get('X-XSRF-TOKEN') == 'mytoken'


def test_login_appliance_session_id_fallback():
    http = MagicMock()
    http.session.cookies = {'vxoaSessionID': 'sess123'}
    http.session.headers = {}
    http.post.return_value = MagicMock(raise_for_status=MagicMock())
    logger = MagicMock()

    client = ApplianceClient(http, '10.0.0.1', logger)
    client.login('admin', 'pass')

    assert http.session.headers.get('vxoaSessionID') == 'sess123'


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("attr_name, filename", PARSER_CASES, ids=[f for _, f in PARSER_CASES])
def test_parse_and_record(minute_stats, attr_name, filename):
    assert filename in minute_stats.files
    assert isinstance(minute_stats.files[filename], str)

    records = getattr(minute_stats, attr_name)
    assert isinstance(records, list)

    if records:
        store = MetricsStore()
        for row in records:
            _call_record(row, store, BASE_TAGS)
        assert len(store._metrics) > 0


def test_parse_interface_csv_filters_all_traffic(logger):
    csv_content = (
        "ifname,bytes_tx,bytes_rx,fwdrops_bytes_tx,fwdrops_bytes_rx,"
        "fwdrops_pkts_tx,fwdrops_pkts_rx,max_bw_tx,max_bw_rx,traftype\n"
        "wan0,100,200,0,0,0,0,1000,1000,pass-through\n"
        "wan0,300,400,0,0,0,0,1000,1000,all traffic\n"
    )
    rows = list(InterfaceStats.parse(csv_content, logger))
    assert len(rows) == 1
    assert rows[0].traftype == 'pass-through'


def test_parse_interface_peak_csv_filters_all_traffic(logger):
    csv_content = (
        "ifname,bytes_tx,bytes_rx,fwdrops_pkts_tx,fwdrops_pkts_rx,"
        "fwdrops_bytes_tx,fwdrops_bytes_rx,max_bw_tx,max_bw_rx,traftype\n"
        "wan0,100,200,0,0,0,0,1000,1000,pass-through\n"
        "wan0,300,400,0,0,0,0,1000,1000,all traffic\n"
    )
    rows = list(InterfacePeakStats.parse(csv_content, logger))
    assert len(rows) == 1
    assert rows[0].traftype == 'pass-through'


def test_parse_interface_overlay_filters_non_breakout():
    csv_content = (
        "ifname,bytes_tx,bytes_rx,max_bw_tx,max_bw_rx,tuntype\nwan0,100,200,1000,1000,2\nwan1,300,400,1000,1000,1\n"
    )
    rows = list(InterfaceOverlayStats.parse(csv_content))
    assert len(rows) == 1
    assert rows[0].ifname == 'wan0'


@pytest.mark.parametrize("parser_cls", EMPTY_PARSE_CASES, ids=[c.__name__ for c in EMPTY_PARSE_CASES])
def test_parse_empty(parser_cls, logger):
    assert _parse(parser_cls, '', logger) == []


def test_parse_dscp_csv_filters_all_traffic():
    csv_content = (
        "dscp,bytes_wtx,bytes_wrx,bytes_ltx,bytes_lrx,traftype\n"
        "be,100,200,300,400,pass-through\n"
        "be,500,600,700,800,all traffic\n"
    )
    rows = list(DscpStats.parse(csv_content))
    assert len(rows) == 1
    assert rows[0].traftype == 'pass-through'


def test_interface_stats_record_skips_utilization_when_max_bw_zero(logger):
    csv_content = (
        "ifname,bytes_tx,bytes_rx,fwdrops_bytes_tx,fwdrops_bytes_rx,"
        "fwdrops_pkts_tx,fwdrops_pkts_rx,max_bw_tx,max_bw_rx,traftype\n"
        "wan0,6000,3000,0,0,0,0,0,0,pass-through\n"
    )
    rows = list(InterfaceStats.parse(csv_content, logger))
    store = MetricsStore()
    rows[0].record(store, ['base:tag'], 'default:10.0.0.1')

    assert not any(k[0].startswith('interface.utilization') for k in store._metrics)


# ---------------------------------------------------------------------------
# Check integration
# ---------------------------------------------------------------------------


def test_all_metrics_covered(all_metrics_aggregator):
    all_metrics_aggregator.assert_metrics_using_metadata(get_metadata_metrics())


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
        if not metric_name.startswith(f'{NS}.'):
            continue
        for stub in all_metrics_aggregator.metrics(metric_name):
            missing = [t for t in BASE_DEVICE_TAGS if t not in stub.tags]
            assert not missing, f'{metric_name} is missing base device tags {missing}; got {stub.tags}'


def test_collection_step_failure_does_not_block_others(dd_run_check, aggregator, mocker, check):
    tgz_bytes = TGZ_FILES[0].read_bytes()
    client = _mock_appliance_client(tgz_bytes, cpu=42)
    client.get_network_interfaces.side_effect = Exception('network error')
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=client)

    dd_run_check(check)

    aggregator.assert_metric(f'{NS}.device.cpu.usage', count=5)
    aggregator.assert_metric(f'{NS}.device.cpu.usage', value=58.0, tags=BASE_DEVICE_TAGS + ['cpu_state:idle'])
    aggregator.assert_metric(f'{NS}.device.hardware.ok', count=1)


def test_up_to_date_appliance_skips_minute_stats_recording(dd_run_check, aggregator, mocker, check):
    tgz_bytes = TGZ_FILES[0].read_bytes()
    client = _mock_appliance_client(tgz_bytes)
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=client, cached_timestamp=str(NEWEST_TS))

    dd_run_check(check)

    check.write_persistent_cache.assert_not_called()


def test_ndm_metadata_submitted(dd_run_check, aggregator, mocker, check):
    tgz_bytes = TGZ_FILES[0].read_bytes()

    client = _mock_appliance_client(tgz_bytes)
    client.get_network_interfaces.return_value = {
        'ifInfo': [
            {'ifname': 'wan0', 'mac': 'aa:bb:cc:dd:ee:ff', 'admin': True, 'oper': True, 'speed': '1000Mb/s (auto)'},
            {'ifname': 'wan0:v100', 'admin': False, 'oper': None},
        ]
    }

    overlay_map = {'0': 'business'}
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD, appliance_client=client, overlay_map=overlay_map)

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
    assert len(interfaces) == 2
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
    assert vlan_iface['oper_status'] == 2

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

    # Tunnels: alias that does not match the ``to_<peer>_<color>`` pattern
    non_matching = by_alias['pass-through-unshaped']
    assert non_matching['dst_device_id'] == ''
    assert non_matching['dst_site_id'] == 'unknown'
    assert non_matching['tunnel_color'] == ''

    # Payload batching and namespace propagation
    for payload in payloads:
        size = len(payload.get('devices', [])) + len(payload.get('interfaces', [])) + len(payload.get('tunnels', []))
        assert 0 < size <= PAYLOAD_METADATA_BATCH_SIZE
        assert payload['namespace'] == 'default'
        assert payload['collect_timestamp'] is not None


def test_stale_appliance_clients_cleaned_up(dd_run_check, mocker, check):
    client = MagicMock()

    # First run: orch returns appliances at 10.0.0.1 and 10.0.0.99
    payload_with_extra = APPLIANCE_PAYLOAD[:1] + [
        {**APPLIANCE_PAYLOAD[0], 'ip': '10.0.0.99', 'hostName': 'StaleAppliance'},
    ]
    _setup_mocks(mocker, check, payload_with_extra, appliance_client=client)
    dd_run_check(check)

    check._appliance_clients['10.0.0.1'] = MagicMock()
    check._appliance_clients['10.0.0.99'] = MagicMock()
    assert '10.0.0.99' in check._appliance_clients

    # Second run: orch no longer returns 10.0.0.99
    _setup_mocks(mocker, check, APPLIANCE_PAYLOAD[:1], appliance_client=client)
    dd_run_check(check)

    assert '10.0.0.1' in check._appliance_clients
    assert '10.0.0.99' not in check._appliance_clients
