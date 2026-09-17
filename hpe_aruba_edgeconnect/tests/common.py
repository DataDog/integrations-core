# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock

from datadog_checks.hpe_aruba_edgeconnect.client import OrchestratorClient

FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def _pack_dir_to_tgz_bytes(directory: Path, file_overrides: dict[str, str] | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        if not file_overrides:
            tf.add(directory, arcname=directory.name)
        else:
            for path in sorted(directory.iterdir()):
                arcname = f'{directory.name}/{path.name}'
                data = file_overrides.get(path.name)
                if data is None:
                    tf.add(path, arcname=arcname)
                    continue
                encoded = data.encode('utf-8')
                info = tarfile.TarInfo(arcname)
                info.size = len(encoded)
                tf.addfile(info, io.BytesIO(encoded))
    return buf.getvalue()


MINUTE_STATS_DIRS = sorted(p for p in FIXTURE_DIR.iterdir() if p.is_dir() and p.name.startswith('st2-'))
TGZ_BYTES = [_pack_dir_to_tgz_bytes(d) for d in MINUTE_STATS_DIRS]
NEWEST_TS = 100000060
TGZ_DATA = {f'{d.name}.tgz': data for d, data in zip(MINUTE_STATS_DIRS, TGZ_BYTES)}
CHECK_MODULE = 'datadog_checks.hpe_aruba_edgeconnect.check'
NS = 'hpe_aruba_edgeconnect'
DEVICE_ID = 'default:10.0.0.1'
NDM_IFACE_RES = f'dd.internal.resource:ndm_interface:{DEVICE_ID}'
EXCLUDED_APPLIANCE_IP = '10.0.0.3'

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

APPLIANCE_BY_IP = {a['ip']: a for a in APPLIANCE_PAYLOAD}


def _build_system_info(ip: str) -> dict:
    """Build a system_info payload that matches the appliance in APPLIANCE_PAYLOAD for the given IP."""
    appliance = APPLIANCE_BY_IP.get(ip, APPLIANCE_PAYLOAD[0])
    version = appliance['softwareVersion']
    return {
        'hostName': appliance['hostName'],
        'applianceid': 193645,
        'model': f'{appliance["model"]} 209005002001 Rev 102786',
        'modelShort': appliance['model'],
        'platform': 'VMware',
        'status': 'Normal',
        'uptime': 816745152,
        'uptimeString': '9d 10h 52m 25s',
        'datetime': '2026/05/08 07:53:33 Etc/UTC',
        'timezone': 'Etc/UTC',
        'gmtOffset': 0,
        'release': f'ECOS {version}_102786',
        'releaseWithoutPrefix': f'{version}_102786',
        'serial': appliance['serial'],
        'uuid': '3dbcbf55-33e0-418f-b98c-3626f98cb0da',
        'nepk': '',
        'portalObjectId': '69f11f4fa66feceed31bde83',
        'deploymentMode': appliance['mode'],
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


SYSTEM_INFO_PAYLOAD = _build_system_info('10.0.0.1')

EXPECTED_METRIC_COUNTS = {
    # Device health (orchestrator + appliance client)
    'orchestrator.reachability': 1,
    'device.reachability': 1,
    'device.uptime': 1,
    'device.cpu.usage': 4,
    'device.memory.usage': 1,
    'device.disk.usage': 5,
    'device.hardware.ok': 1,
    'interface.status': 2,
    'interface.speed': 1,
    'interface.bandwidth.tx.count': 5,
    'interface.bandwidth.rx.count': 5,
    'interface.bandwidth.tx.rate': 5,
    'interface.bandwidth.rx.rate': 5,
    'interface.bandwidth.tx.max': 5,
    'interface.bandwidth.rx.max': 5,
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
    'interface.utilization.tx.avg': 5,
    'interface.utilization.rx.avg': 5,
    'interface.utilization.tx.max': 5,
    'interface.utilization.rx.max': 5,
    'tunnel.throughput.tx.bytes.count': 58,
    'tunnel.throughput.rx.bytes.count': 58,
    'tunnel.throughput.tx.bytes.rate': 58,
    'tunnel.throughput.rx.bytes.rate': 58,
    'tunnel.throughput.tx.packets.count': 58,
    'tunnel.throughput.rx.packets.count': 58,
    'tunnel.throughput.tx.packets.rate': 58,
    'tunnel.throughput.rx.packets.rate': 58,
    'tunnel.throughput.tx.bytes.max': 58,
    'tunnel.throughput.rx.bytes.max': 58,
    'tunnel.throughput.tx.packets.max': 58,
    'tunnel.throughput.rx.packets.max': 58,
    'tunnel.latency': 29,
    'tunnel.latency.min': 29,
    'tunnel.latency.max': 29,
    'tunnel.loss': 58,
    'tunnel.jitter': 31,
    'tunnel.jitter.max': 31,
    'tunnel.qoe.mos': 62,
    'tunnel.qoe.mos.min': 62,
    'tunnel.availability': 29,
    'tunnel.internet_breakout.bandwidth.tx.count': 2,
    'tunnel.internet_breakout.bandwidth.rx.count': 2,
    'tunnel.internet_breakout.bandwidth.tx.rate': 2,
    'tunnel.internet_breakout.bandwidth.rx.rate': 2,
    'tunnel.internet_breakout.bandwidth.tx.max': 2,
    'tunnel.internet_breakout.bandwidth.rx.max': 2,
    'circuit.sla.latency': 4,
    'circuit.sla.loss': 4,
    'circuit.sla.jitter': 4,
    'nexthop.status': 8,
    'qos.class.drops': 8,
    'qos.class.drop.percentage': 4,
    'qos.class.bandwidth.tx.count': 6,
    'qos.class.bandwidth.rx.count': 6,
    'qos.class.bandwidth.tx.rate': 6,
    'qos.class.bandwidth.rx.rate': 6,
    'qos.class.bandwidth.tx.max': 6,
    'qos.class.bandwidth.rx.max': 6,
    'application.latency': 6,
}

BASE_DEVICE_TAGS = [
    'orch_ip:localhost:8443',
    'device_namespace:default',
    'device_ip:10.0.0.1',
    'device_model:EC-V',
    'device_hostname:SydneySP01',
    'software_version:9.3.1',
    'device_vendor:aruba',
    'site_id:SYD',
    'site_name:SYD',
    'dd.internal.resource:ndm_device:default:10.0.0.1',
    'dd.internal.resource:ndm_device_user_tags:default:10.0.0.1',
]

EXPECTED_VALUES = [
    ('device.reachability', 1, []),
    ('device.uptime', 816745.152, []),
    ('device.cpu.usage', 30.0, ['cpu_state:user']),
    ('device.cpu.usage', 15.0, ['cpu_state:system']),
    ('device.cpu.usage', 3.0, ['cpu_state:irq']),
    ('device.cpu.usage', 2.0, ['cpu_state:nice']),
    ('device.memory.usage', (3174232 / 3945080) * 100.0, []),
    ('device.disk.usage', 21.0, ['mount:/']),
    ('device.disk.usage', 11.0, ['mount:/var']),
    ('device.hardware.ok', 0, []),
    ('interface.status', 1, ['interface_name:wan0', 'status_type:admin', NDM_IFACE_RES]),
    ('interface.status', 1, ['interface_name:wan0', 'status_type:oper', NDM_IFACE_RES]),
    ('interface.speed', 1000000000, ['interface_name:wan0', NDM_IFACE_RES]),
    (
        'interface.bandwidth.tx.count',
        158508,
        ['interface_name:wan0', 'traffic_type:pass-through-unshaped', NDM_IFACE_RES],
    ),
    (
        'interface.bandwidth.tx.rate',
        1320.9,
        ['interface_name:wan0', 'traffic_type:pass-through-unshaped', NDM_IFACE_RES],
    ),
    (
        'interface.bandwidth.rx.count',
        82824,
        ['interface_name:wan0', 'traffic_type:pass-through-unshaped', NDM_IFACE_RES],
    ),
    (
        'interface.bandwidth.tx.max',
        1332,
        ['interface_name:wan0', 'traffic_type:pass-through-unshaped', NDM_IFACE_RES],
    ),
    (
        'interface.bandwidth.rx.max',
        696,
        ['interface_name:wan0', 'traffic_type:pass-through-unshaped', NDM_IFACE_RES],
    ),
    (
        'tunnel.latency',
        1.4,
        [
            'tunnel_name:tunnel_12',
            'tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1',
            'overlay_name:business',
            'is_sdwan:false',
        ],
    ),
    (
        'tunnel.latency.min',
        1.38,
        [
            'tunnel_name:tunnel_12',
            'tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1',
            'overlay_name:business',
            'is_sdwan:false',
        ],
    ),
    (
        'tunnel.jitter',
        350,
        [
            'tunnel_name:bondedTunnel_16',
            'tunnel_alias:to_NewYorkSP01_CriticalApps',
            'is_sdwan:false',
        ],
    ),
    (
        'tunnel.jitter.max',
        6,
        [
            'tunnel_name:bondedTunnel_16',
            'tunnel_alias:to_NewYorkSP01_CriticalApps',
            'is_sdwan:false',
        ],
    ),
    (
        'tunnel.qoe.mos',
        4.0,
        [
            'tunnel_name:tunnel_12',
            'tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1',
            'overlay_name:business',
            'is_sdwan:false',
            'fec:post',
        ],
    ),
    (
        'tunnel.qoe.mos.min',
        4.0,
        [
            'tunnel_name:tunnel_12',
            'tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1',
            'overlay_name:business',
            'is_sdwan:false',
            'fec:post',
        ],
    ),
    ('tunnel.internet_breakout.bandwidth.tx.count', 76012, ['interface_name:wan0', NDM_IFACE_RES]),
    ('tunnel.internet_breakout.bandwidth.tx.rate', 316.71666666666664, ['interface_name:wan0', NDM_IFACE_RES]),
    ('tunnel.internet_breakout.bandwidth.rx.max', 100000, ['interface_name:wan0', NDM_IFACE_RES]),
    ('qos.class.bandwidth.tx.count', 75684, ['dscp:be', 'traffic_type:pass-through-unshaped', 'side:wan']),
    ('qos.class.bandwidth.tx.rate', 630.7, ['dscp:be', 'traffic_type:pass-through-unshaped', 'side:wan']),
    ('qos.class.bandwidth.tx.max', 636, ['dscp:be', 'traffic_type:pass-through-unshaped', 'side:wan']),
    ('qos.class.drops', 0, ['overlay_name:BulkData', 'drop_type:qos', 'direction:inbound']),
    ('qos.class.drop.percentage', 0, ['overlay_name:BulkData', 'direction:inbound']),
    ('circuit.sla.latency', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.loss', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.jitter', 59.5, ['probe_name:om_passThrough_9']),
    ('nexthop.status', 60, ['probe_name:om_passThrough_6', 'status_type:admin']),
    ('nexthop.status', 0, ['probe_name:om_passThrough_6', 'status_type:oper']),
    ('application.latency', 5.1, ['application:microsoft', 'tunnel_name:bondedTunnel_16', 'latency_type:cnd']),
]

ALARM_PAYLOAD = {
    'outstanding': [
        {
            'severity': 1,
            'sequenceId': 3777,
            'source': 'System',
            'acknowledged': False,
            'clearable': False,
            'time': 1779178081000,
            'description': 'All NTP servers are unreachable',
            'type': 'SW',
            'recommendation': (
                "Check appliance's NTP server IP and version config. Can appliance reach the NTP server? "
                "Is UDP port 123 open between Appliance's mgmt0 IP and NTP server?"
            ),
            'serviceAffect': True,
            'typeId': 262153,
            'name': 'ntpd_server_unreachable',
            'occurrenceCount': 1,
            'active': True,
            'ackedBy': '',
            'ackedTime': 0,
            'clearedBy': '',
            'clearedTime': 0,
            'note': '',
        }
    ],
    'summary': {
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
}

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
    return {
        'latestTimestamp': NEWEST_TS,
        'data': [
            {
                str(NEWEST_TS): [
                    {
                        'cpu_number': 'ALL',
                        'pUser': str(usage * 0.6),
                        'pSys': str(usage * 0.3),
                        'pIRQ': str(usage * 0.06),
                        'pNice': str(usage * 0.04),
                    },
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Mock client builders
# ---------------------------------------------------------------------------


def _mock_orch_client(appliance_payload, overlay_config=None):
    overlays_response = MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(return_value=overlay_config if overlay_config is not None else []),
    )

    def http_get(url, **kwargs):
        if url.endswith('/gms/rest/gms/overlays/config'):
            return overlays_response
        raise AssertionError(f'unexpected orchestrator GET request: {url}')

    http = MagicMock()
    http.get.side_effect = http_get
    client = OrchestratorClient(http, 'localhost:8443')
    client.get_appliances = MagicMock(return_value=appliance_payload)
    return client


def _mock_appliance_client(
    tgz_data,
    newest_timestamp=NEWEST_TS,
    cpu=50,
    mem=None,
    disk=None,
    alarms=None,
    system_info=None,
    app_ip='10.0.0.1',
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
    client.get_system_info.return_value = system_info if system_info is not None else _build_system_info(app_ip)
    client.get_interface_labels.return_value = {'wan': {}, 'lan': {}}
    client.app_ip = app_ip
    return client


def _setup_mocks(
    mocker,
    check,
    appliance_payload,
    tgz_bytes=None,
    appliance_client=None,
    overlay_config=None,
    cached_timestamp=None,
):
    orch = _mock_orch_client(appliance_payload, overlay_config)
    mocker.patch(f'{CHECK_MODULE}.OrchestratorClient', return_value=orch)
    check._orch_client = None

    if appliance_client is not None:
        mocker.patch.object(check, '_create_appliance_client', return_value=appliance_client)
    elif tgz_bytes is not None:
        mocker.patch.object(check, '_create_appliance_client', return_value=_mock_appliance_client(tgz_bytes))

    mocker.patch.object(check, 'read_persistent_cache', return_value=cached_timestamp)
    mocker.patch.object(check, 'write_persistent_cache')
    return orch


# ---------------------------------------------------------------------------
# E2E expectations
# ---------------------------------------------------------------------------

E2E_TUNNEL_AGGREGATE_ALIASES = ('all traffic', 'optimized traffic', 'pass-through', 'pass-through-unshaped')

E2E_EXPECTED_METRIC_COUNTS = {
    'orchestrator.reachability': 1,
    'device.reachability': 2,
    'device.uptime': 1,
    'device.cpu.usage': 4,
    'device.memory.usage': 1,
    'device.disk.usage': 5,
    'device.hardware.ok': 1,
    'interface.status': 2,
    'interface.speed': 1,
    'interface.bandwidth.tx.count': 3,
    'interface.bandwidth.rx.count': 3,
    'interface.bandwidth.tx.rate': 3,
    'interface.bandwidth.rx.rate': 3,
    'interface.bandwidth.tx.max': 3,
    'interface.bandwidth.rx.max': 3,
    'interface.drops.bytes.tx.count': 3,
    'interface.drops.bytes.rx.count': 3,
    'interface.drops.bytes.tx.rate': 3,
    'interface.drops.bytes.rx.rate': 3,
    'interface.drops.bytes.tx.max': 3,
    'interface.drops.bytes.rx.max': 3,
    'interface.drops.packets.tx.count': 3,
    'interface.drops.packets.rx.count': 3,
    'interface.drops.packets.tx.rate': 3,
    'interface.drops.packets.rx.rate': 3,
    'interface.drops.packets.tx.max': 3,
    'interface.drops.packets.rx.max': 3,
    'interface.utilization.tx.avg': 3,
    'interface.utilization.rx.avg': 3,
    'interface.utilization.tx.max': 3,
    'interface.utilization.rx.max': 3,
    'tunnel.throughput.tx.bytes.count': 58,
    'tunnel.throughput.rx.bytes.count': 58,
    'tunnel.throughput.tx.bytes.rate': 58,
    'tunnel.throughput.rx.bytes.rate': 58,
    'tunnel.throughput.tx.packets.count': 58,
    'tunnel.throughput.rx.packets.count': 58,
    'tunnel.throughput.tx.packets.rate': 58,
    'tunnel.throughput.rx.packets.rate': 58,
    'tunnel.throughput.tx.bytes.max': 58,
    'tunnel.throughput.rx.bytes.max': 58,
    'tunnel.throughput.tx.packets.max': 58,
    'tunnel.throughput.rx.packets.max': 58,
    'tunnel.latency': 29,
    'tunnel.latency.min': 29,
    'tunnel.latency.max': 29,
    'tunnel.loss': 58,
    'tunnel.jitter': 31,
    'tunnel.jitter.max': 31,
    'tunnel.qoe.mos': 62,
    'tunnel.qoe.mos.min': 62,
    'tunnel.availability': 29,
    'tunnel.internet_breakout.bandwidth.tx.count': 1,
    'tunnel.internet_breakout.bandwidth.rx.count': 1,
    'tunnel.internet_breakout.bandwidth.tx.rate': 1,
    'tunnel.internet_breakout.bandwidth.rx.rate': 1,
    'tunnel.internet_breakout.bandwidth.tx.max': 1,
    'tunnel.internet_breakout.bandwidth.rx.max': 1,
    'circuit.sla.latency': 4,
    'circuit.sla.loss': 4,
    'circuit.sla.jitter': 4,
    'nexthop.status': 8,
    'qos.class.drops': 4,
    'qos.class.drop.percentage': 2,
    'qos.class.bandwidth.tx.count': 4,
    'qos.class.bandwidth.rx.count': 4,
    'qos.class.bandwidth.tx.rate': 4,
    'qos.class.bandwidth.rx.rate': 4,
    'qos.class.bandwidth.tx.max': 4,
    'qos.class.bandwidth.rx.max': 4,
    'application.latency': 6,
}

E2E_EXPECTED_VALUES = [
    ('device.reachability', 1, []),
    ('device.uptime', 86400, []),
    ('device.cpu.usage', 30.0, ['cpu_state:user']),
    ('device.cpu.usage', 15.0, ['cpu_state:system']),
    ('device.cpu.usage', 3.0, ['cpu_state:irq']),
    ('device.cpu.usage', 2.0, ['cpu_state:nice']),
    ('device.memory.usage', (3174232 / 3945080) * 100.0, []),
    ('device.disk.usage', 21.0, ['mount:/']),
    ('device.disk.usage', 11.0, ['mount:/var']),
    ('device.hardware.ok', 1, []),
    ('interface.status', 1, ['interface_name:wan0', 'status_type:admin']),
    ('interface.status', 1, ['interface_name:wan0', 'status_type:oper']),
    ('interface.speed', 1000000000, ['interface_name:wan0']),
    ('interface.bandwidth.tx.count', 79920, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.tx.rate', 1332.0, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.count', 41760, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.tx.max', 1332, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.max', 696, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('tunnel.latency', 1.39, ['tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1']),
    ('tunnel.latency.min', 1.38, ['tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1']),
    ('tunnel.jitter', 600, ['tunnel_name:bondedTunnel_16']),
    ('tunnel.jitter.max', 6, ['tunnel_name:bondedTunnel_16']),
    ('tunnel.qoe.mos', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    ('tunnel.qoe.mos.min', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    ('tunnel.internet_breakout.bandwidth.tx.count', 38160, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.tx.rate', 636.0, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.rx.max', 100000, ['interface_name:wan0']),
    ('qos.class.bandwidth.tx.count', 38160, ['dscp:be', 'side:wan']),
    ('qos.class.bandwidth.tx.rate', 636.0, ['dscp:be', 'side:wan']),
    ('qos.class.bandwidth.tx.max', 636, ['dscp:be', 'side:wan']),
    ('qos.class.drops', 0, ['overlay_name:BulkData', 'drop_type:qos']),
    ('qos.class.drop.percentage', 0, ['overlay_name:BulkData']),
    ('circuit.sla.latency', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.loss', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.jitter', 60, ['probe_name:om_passThrough_9']),
    ('nexthop.status', 60, ['probe_name:om_passThrough_6', 'status_type:admin']),
    ('nexthop.status', 0, ['probe_name:om_passThrough_6', 'status_type:oper']),
    ('application.latency', 5.0, ['application:microsoft', 'tunnel_name:bondedTunnel_16', 'latency_type:cnd']),
]
