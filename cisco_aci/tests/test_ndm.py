# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.cisco_aci import ndm


class TestGetRemoteDeviceDdId:
    """Test the get_remote_device_dd_id function with various scenarios"""

    def test_get_remote_device_dd_id_skip_ip_match_with_non_matching_ip(self):
        """Test that device is returned when skip_ip_match is True, even with non-matching IP"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.101.0',
            'topology/pod-1/node-102': 'default:10.0.102.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn)

        assert result == 'default:10.0.101.0'

    def test_get_remote_device_dd_id_device_not_in_map_skip_ip_match(self):
        """Test that None is returned when device is not in the device_map, even with skip_ip_match True"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.101.0',
        }
        remote_device_dn = 'topology/pod-1/node-999'  # Not in map

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn)

        assert result is None


class TestCreateTopologyLinkMetadata:
    """Test the create_topology_link_metadata function"""

    def test_create_topology_with_conflicting_ips(self):
        """Test that topology links are created even when IP doesn't match"""
        import logging

        logger = logging.getLogger('test')

        lldp_adj_eps = [
            {
                'lldpAdjEp': {
                    'attributes': {
                        'dn': 'topology/pod-1/node-101/sys/lldp/inst/if-[eth1/49]/adj-1',
                        'chassisIdV': '6a:00:21:1f:55:2a',
                        'chassisIdT': 'mac',
                        'portIdV': '6a:00:21:1f:55:2a',
                        'portIdT': 'mac',
                        'portDesc': 'topology/pod-1/paths-201/pathep-[eth5/1]',
                        'sysName': 'SP201',
                        'sysDesc': 'topology/pod-1/node-201',
                        'mgmtIp': '192.168.1.100',  # OOB Management IP
                    }
                }
            }
        ]
        cdp_adj_eps = []
        device_map = {
            'pod-1-node-101': 'default:10.0.200.0',
            'pod-1-node-201': 'default:10.0.200.5',
        }
        namespace = 'default'

        links = list(ndm.create_topology_link_metadata(logger, lldp_adj_eps, cdp_adj_eps, device_map, namespace))

        assert len(links) == 1
        link = links[0]

        assert link.remote.device.dd_id == 'default:10.0.200.5'
        assert link.remote.interface.dd_id == 'default:10.0.200.5:cisco-aci-eth5/1'
        assert (
            link.remote.device.ip_address == '192.168.1.100'
        )  # this IP is still set, but the dd_id should use the correct IP now.

        assert link.local.device.dd_id == 'default:10.0.200.0'
        assert link.local.interface.dd_id == 'default:10.0.200.0:cisco-aci-eth1/49'

    def test_create_topology_with_matching_ip(self):
        """Test that topology links work normally when IP matches"""
        import logging

        logger = logging.getLogger('test')

        lldp_adj_eps = [
            {
                'lldpAdjEp': {
                    'attributes': {
                        'dn': 'topology/pod-1/node-101/sys/lldp/inst/if-[eth1/49]/adj-1',
                        'chassisIdV': '6a:00:21:1f:55:2a',
                        'chassisIdT': 'mac',
                        'portIdV': '6a:00:21:1f:55:2a',
                        'portIdT': 'mac',
                        'portDesc': 'topology/pod-1/paths-201/pathep-[eth5/1]',
                        'sysName': 'SP201',
                        'sysDesc': 'topology/pod-1/node-201',
                        'mgmtIp': '10.0.200.5',  # Matching IP (ends with device ID IP)
                    }
                }
            }
        ]
        cdp_adj_eps = []
        device_map = {
            'pod-1-node-101': 'default:10.0.200.0',
            'pod-1-node-201': 'default:10.0.200.5',
        }
        namespace = 'default'

        # Test with skip_ip_match=False
        links = list(ndm.create_topology_link_metadata(logger, lldp_adj_eps, cdp_adj_eps, device_map, namespace))

        assert len(links) == 1
        link = links[0]
        assert link.local.device.dd_id == 'default:10.0.200.0'
        assert link.local.interface.dd_id == 'default:10.0.200.0:cisco-aci-eth1/49'

        assert link.remote.device.dd_id == 'default:10.0.200.5'
        assert link.remote.interface.dd_id == 'default:10.0.200.5:cisco-aci-eth5/1'

        # Test with skip_ip_match=True - should also work
        links = list(ndm.create_topology_link_metadata(logger, lldp_adj_eps, cdp_adj_eps, device_map, namespace))

        assert len(links) == 1
        link = links[0]
        assert link.local.device.dd_id == 'default:10.0.200.0'
        assert link.local.interface.dd_id == 'default:10.0.200.0:cisco-aci-eth1/49'

        assert link.remote.device.dd_id == 'default:10.0.200.5'
        assert link.remote.interface.dd_id == 'default:10.0.200.5:cisco-aci-eth5/1'
