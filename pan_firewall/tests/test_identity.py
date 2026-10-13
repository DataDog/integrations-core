# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import dataclasses

import pytest

from datadog_checks.pan_firewall.auth import Credentials
from datadog_checks.pan_firewall.firewalls import FirewallTarget
from datadog_checks.pan_firewall.identity import device_ip, global_tags, parse_system_info, vsys_list
from datadog_checks.pan_firewall.xml_utils import parse_response

from .common import FIXTURES
from .fixture_map import op_fixture

SYSTEM_INFO_CMD = '<show><system><info/></system></show>'
SERIAL = '007955000930601'
CREDS = Credentials(username='dummy-user', password='dummy-password', api_key=None)
STATIC_TARGET = FirewallTarget(ip='3.13.247.39', port=443, credentials=CREDS)
# A Panorama-discovered fw-a polled through a `firewall_ip_overrides` entry: it connects to the public IP, but the
# device is the one Panorama reports.
PANORAMA_TARGET = FirewallTarget(
    ip='3.13.247.39', port=443, credentials=CREDS, serial=SERIAL, hostname='fw-a', reported_ip='10.60.0.10'
)
FW_A = parse_system_info(parse_response(op_fixture(SYSTEM_INFO_CMD).read_bytes()))


def ifnet_rows(path):
    return parse_response(path.read_bytes()).findall('./result/ifnet/entry')


def test_parse_system_info_fw_a():
    assert (FW_A.serial, FW_A.hostname, FW_A.model, FW_A.family, FW_A.own_ip) == (
        SERIAL,
        'fw-a',
        'PA-VM',
        'vm',
        '10.60.0.10',
    )
    assert (FW_A.sw_version, FW_A.multi_vsys, FW_A.advanced_routing) == ('11.1.13-h12', False, False)
    assert FW_A.clock == 'Fri Oct  2 04:49:06 2026'


@pytest.mark.parametrize(
    'target, expected',
    [
        pytest.param(STATIC_TARGET, '3.13.247.39', id='static-uses-config-ip'),
        pytest.param(PANORAMA_TARGET, '10.60.0.10', id='panorama-uses-reported-ip-not-override'),
    ],
)
def test_device_ip(target, expected):
    assert device_ip(target) == expected


def test_global_tags_with_identity():
    tags = global_tags(FW_A, STATIC_TARGET, 'default', ['env:lab'])

    assert sorted(tags) == sorted(
        [
            'device_namespace:default',
            'device_ip:3.13.247.39',
            f'device_id:{SERIAL}',
            'device_hostname:fw-a',
            f'device_serial:{SERIAL}',
            'device_model:PA-VM',
            'device_family:vm',
            'device_vendor:paloaltonetworks',
            'os_version:11.1.13-h12',
            'multi_vsys:false',
            'advanced_routing:false',
            'env:lab',
            f'dd.internal.resource:ndm_device:{SERIAL}',
            f'dd.internal.resource:ndm_device_user_tags:{SERIAL}',
        ]
    )


def test_global_tags_before_a_static_firewall_ever_answered():
    tags = global_tags(None, STATIC_TARGET, 'default', ['env:lab'])

    assert sorted(tags) == [
        'device_ip:3.13.247.39',
        'device_namespace:default',
        'device_vendor:paloaltonetworks',
        'env:lab',
    ]


def test_global_tags_take_serial_and_hostname_from_panorama_discovery():
    tags = global_tags(None, PANORAMA_TARGET, 'default', [])

    assert sorted(tags) == sorted(
        [
            'device_namespace:default',
            'device_ip:10.60.0.10',
            f'device_id:{SERIAL}',
            'device_hostname:fw-a',
            f'device_serial:{SERIAL}',
            'device_vendor:paloaltonetworks',
            f'dd.internal.resource:ndm_device:{SERIAL}',
            f'dd.internal.resource:ndm_device_user_tags:{SERIAL}',
        ]
    )


@pytest.mark.parametrize(
    'identity, rows_file, configured, expected',
    [
        pytest.param(FW_A, 'fw-a-probe/interface_all.xml', None, ['vsys1'], id='single-vsys'),
        pytest.param(
            dataclasses.replace(FW_A, multi_vsys=True),
            'synthetic/interface_all_multi_vsys.xml',
            None,
            ['vsys1', 'vsys2'],
            id='multi-vsys-from-interface-rows',
        ),
        pytest.param(
            dataclasses.replace(FW_A, multi_vsys=True),
            'synthetic/interface_all_multi_vsys.xml',
            ['3', 'vsys1'],
            ['vsys3', 'vsys1'],
            id='configured-wins',
        ),
    ],
)
def test_vsys_list(identity, rows_file, configured, expected):
    assert vsys_list(identity, ifnet_rows(FIXTURES / rows_file), configured) == expected
