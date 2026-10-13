# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Maps a PAN-OS API request to a captured fixture file.

Shared by the unit fake transport and the docker fakes, so both answer from the same data.
"""

from pathlib import Path

from .common import FIXTURES

# `type=op` commands, as sent by the live captures, to the fixture file name.
OP_FIXTURES = {
    '<show><system><info/></system></show>': 'system_info.xml',
    '<show><routing><protocol><bgp><peer/></bgp></protocol></routing></show>': 'bgp_peer_legacy.xml',
    '<show><routing><protocol><ospf><neighbor/></ospf></protocol></routing></show>': 'ospf_neighbor_legacy.xml',
    '<show><running><resource-monitor><minute><last>1</last></minute></resource-monitor></running></show>': (
        'resource_monitor.xml'
    ),
    '<show><system><disk-space/></system></show>': 'disk_space.xml',
    '<show><rule-hit-count><vsys><vsys-name><entry name=\'vsys1\'><rule-base><entry name=\'security\'>'
    '<rules><all/></rules></entry></rule-base></entry></vsys-name></vsys></rule-hit-count></show>': (
        'rule_hit_count.xml'
    ),
    '<show><counter><global/></counter></show>': 'counter_global.xml',
    '<show><high-availability><all/></high-availability></show>': 'ha_all.xml',
    '<show><vpn><flow/></vpn></show>': 'vpn_flow.xml',
    '<show><vpn><gateway/></vpn></show>': 'vpn_gateway.xml',
    '<request><license><info/></license></request>': 'license_info.xml',
    '<show><counter><interface>all</interface></counter></show>': 'counter_interface.xml',
    '<show><system><environmentals/></system></show>': 'environmentals.xml',
    '<show><system><resources/></system></show>': 'system_resources.xml',
}


def op_fixture(cmd: str, firewall: str = 'fw-a') -> Path:
    """Return the fixture answering `type=op&cmd=<cmd>` for the given firewall set (`fw-a` or `fw-b`)."""
    return FIXTURES / firewall / OP_FIXTURES[cmd]
