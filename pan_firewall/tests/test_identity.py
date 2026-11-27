# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import dataclasses

import pytest

from datadog_checks.pan_firewall.auth import Credentials
from datadog_checks.pan_firewall.firewalls import FirewallTarget
from datadog_checks.pan_firewall.identity import global_tags, parse_system_info, vsys_list
from datadog_checks.pan_firewall.xml_utils import parse_response

from .common import FIXTURES, FW_A_DEVICE_TAGS, FW_A_IP, FW_A_SERIAL, FW_B_SERIAL, SYSTEM_INFO_CMD
from .fake_panos import FIREWALL_SETS
from .fixture_map import op_fixture
from .helpers import make_instance, new_check

pytestmark = pytest.mark.unit

CREDS = Credentials(username='dummy-user', password='dummy-password', api_key=None)
# A Panorama-discovered fw-a, polled at the IP Panorama reports for it.
PANORAMA_TARGET = FirewallTarget(
    ip='10.20.0.10', credentials=CREDS, serial=FW_A_SERIAL, hostname='fw-a', panorama_host='panorama.example.com'
)
FW_A = parse_system_info(parse_response(op_fixture(SYSTEM_INFO_CMD).read_bytes()))


def ifnet_rows(path):
    return parse_response(path.read_bytes()).findall('./result/ifnet/entry')


def test_parse_system_info_fw_a():
    assert (FW_A.serial, FW_A.hostname, FW_A.model, FW_A.family, FW_A.own_ip) == (
        FW_A_SERIAL,
        'fw-a',
        'PA-VM',
        'vm',
        '10.20.0.10',
    )
    assert (FW_A.sw_version, FW_A.multi_vsys, FW_A.advanced_routing) == ('11.1.13-h12', False, False)


def test_global_tags_with_identity():
    tags = global_tags(FW_A, FirewallTarget(ip=FW_A_IP, credentials=CREDS), 'default', ['team:test'])

    assert sorted(tags) == FW_A_DEVICE_TAGS


def test_global_tags_take_serial_and_hostname_from_panorama_discovery():
    tags = global_tags(None, PANORAMA_TARGET, 'default', [])

    assert sorted(tags) == sorted(
        [
            'device_namespace:default',
            'device_ip:10.20.0.10',
            f'device_id:{FW_A_SERIAL}',
            'device_hostname:fw-a',
            f'device_serial:{FW_A_SERIAL}',
            'device_vendor:paloaltonetworks',
            'panorama_host:panorama.example.com',
        ]
    )


def test_global_tags_use_discovery_model_and_version_until_the_firewall_answers():
    target = dataclasses.replace(PANORAMA_TARGET, model='PA-DISCOVERED', sw_version='10.0.0')

    before = global_tags(None, target, 'default', [])
    after = global_tags(FW_A, target, 'default', [])

    assert {'device_model:PA-DISCOVERED', 'os_version:10.0.0'} <= set(before)
    assert {'device_model:PA-VM', 'os_version:11.1.13-h12'} <= set(after)
    assert not {'device_model:PA-DISCOVERED', 'os_version:10.0.0'} & set(after)


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


def test_static_firewall_replaced_at_the_same_ip_is_tagged_and_tracked_as_the_new_unit(
    dd_run_check, aggregator, fake_panos, monkeypatch, schedule_clock
):
    check = new_check(make_instance())
    dd_run_check(check)
    # The unit is swapped for another one that answers at the same IP; the identity is due again after 30 minutes.
    monkeypatch.setitem(FIREWALL_SETS, FW_A_IP, 'fw-b')
    schedule_clock.now += 1800
    aggregator.reset()

    dd_run_check(check)

    (can_connect,) = aggregator.metrics('pan_firewall.can_connect')
    assert {f'device_id:{FW_B_SERIAL}', f'device_serial:{FW_B_SERIAL}', 'device_hostname:fw-b'} <= set(can_connect.tags)
    assert f'device_id:{FW_A_SERIAL}' not in can_connect.tags
