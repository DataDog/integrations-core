# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.cisco_aci import ndm


class TestGetRemoteDeviceDdId:
    """Test the get_remote_device_dd_id function with various scenarios"""

    def test_get_remote_device_dd_id_with_matching_ip(self):
        """Test that device is returned when IP matches and skip_ip_match is False"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
            'topology/pod-1/node-102': 'default:10.0.200.1',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = '10.0.200.0'
        should_skip_ip_match = False

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result == 'default:10.0.200.0'

    def test_get_remote_device_dd_id_with_non_matching_ip(self):
        """Test that device is NOT returned when IP doesn't match and skip_ip_match is False"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = '10.0.200.99'  # Different IP
        should_skip_ip_match = False

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result is None

    def test_get_remote_device_dd_id_with_none_mgmt_ip(self):
        """Test that device is NOT returned when mgmt_ip is None and skip_ip_match is False"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = None
        should_skip_ip_match = False

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result is None

    def test_get_remote_device_dd_id_with_empty_mgmt_ip(self):
        """Test that device is NOT returned when mgmt_ip is empty string and skip_ip_match is False"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = ''
        should_skip_ip_match = False

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result is None

    def test_get_remote_device_dd_id_skip_ip_match_with_matching_ip(self):
        """Test that device is returned when skip_ip_match is True, even with matching IP"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = '10.0.200.0'
        should_skip_ip_match = True

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result == 'default:10.0.200.0'

    def test_get_remote_device_dd_id_skip_ip_match_with_non_matching_ip(self):
        """Test that device is returned when skip_ip_match is True, even with non-matching IP"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = '10.0.200.99'  # Different IP
        should_skip_ip_match = True

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result == 'default:10.0.200.0'

    def test_get_remote_device_dd_id_skip_ip_match_with_none_mgmt_ip(self):
        """Test that device is returned when skip_ip_match is True, even with None mgmt_ip"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = None
        should_skip_ip_match = True

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result == 'default:10.0.200.0'

    def test_get_remote_device_dd_id_skip_ip_match_with_empty_mgmt_ip(self):
        """Test that device is returned when skip_ip_match is True, even with empty mgmt_ip"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-101'
        mgmt_ip = ''
        should_skip_ip_match = True

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result == 'default:10.0.200.0'

    def test_get_remote_device_dd_id_device_not_in_map(self):
        """Test that None is returned when device is not in the device_map"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-999'  # Not in map
        mgmt_ip = '10.0.200.0'
        should_skip_ip_match = False

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result is None

    def test_get_remote_device_dd_id_device_not_in_map_skip_ip_match(self):
        """Test that None is returned when device is not in the device_map, even with skip_ip_match True"""
        device_map = {
            'topology/pod-1/node-101': 'default:10.0.200.0',
        }
        remote_device_dn = 'topology/pod-1/node-999'  # Not in map
        mgmt_ip = '10.0.200.0'
        should_skip_ip_match = True

        result = ndm.get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip, should_skip_ip_match)

        assert result is None


class TestCreateTopologyLinkMetadata:
    """Test the create_topology_link_metadata function with topology_skips_ip_match"""

    def test_create_topology_with_conflicting_ips_and_skip_ip_match(self):
        """Test that topology links are created even when IP doesn't match if skip_ip_match is True"""
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
        should_topology_skip_ip_match = True

        links = list(
            ndm.create_topology_link_metadata(
                logger, lldp_adj_eps, cdp_adj_eps, device_map, namespace, should_topology_skip_ip_match
            )
        )

        assert len(links) == 1
        link = links[0]

        assert link.remote.device.dd_id == 'default:10.0.200.5'
        assert link.remote.interface.dd_id == 'default:10.0.200.5:cisco-aci-eth5/1'
        assert (
            link.remote.device.ip_address == '192.168.1.100'
        )  # this IP is still set, but the dd_id should use the correct IP now.

        assert link.local.device.dd_id == 'default:10.0.200.0'
        assert link.local.interface.dd_id == 'default:10.0.200.0:cisco-aci-eth1/49'

    def test_create_topology_with_non_matching_ip_and_skip_ip_match_false(self):
        """Test that topology links lack remote dd_id when IP doesn't match and skip_ip_match is False"""
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
        should_topology_skip_ip_match = False

        links = list(
            ndm.create_topology_link_metadata(
                logger, lldp_adj_eps, cdp_adj_eps, device_map, namespace, should_topology_skip_ip_match
            )
        )

        assert len(links) == 1
        link = links[0]
        # With skip_ip_match=False and non-matching IP, remote device should NOT have dd_id
        assert not hasattr(link.remote.device, 'dd_id') or link.remote.device.dd_id is None
        assert not hasattr(link.remote.interface, 'dd_id') or link.remote.interface.dd_id is None
        assert link.remote.device.ip_address == '192.168.1.100'

        assert link.local.device.dd_id == 'default:10.0.200.0'
        assert link.local.interface.dd_id == 'default:10.0.200.0:cisco-aci-eth1/49'

    def test_create_topology_with_matching_ip(self):
        """Test that topology links work normally when IP matches regardless of skip_ip_match setting"""
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
        links = list(ndm.create_topology_link_metadata(logger, lldp_adj_eps, cdp_adj_eps, device_map, namespace, False))

        assert len(links) == 1
        link = links[0]
        assert link.local.device.dd_id == 'default:10.0.200.0'
        assert link.local.interface.dd_id == 'default:10.0.200.0:cisco-aci-eth1/49'

        assert link.remote.device.dd_id == 'default:10.0.200.5'
        assert link.remote.interface.dd_id == 'default:10.0.200.5:cisco-aci-eth5/1'

        # Test with skip_ip_match=True - should also work
        links = list(ndm.create_topology_link_metadata(logger, lldp_adj_eps, cdp_adj_eps, device_map, namespace, True))

        assert len(links) == 1
        link = links[0]
        assert link.local.device.dd_id == 'default:10.0.200.0'
        assert link.local.interface.dd_id == 'default:10.0.200.0:cisco-aci-eth1/49'

        assert link.remote.device.dd_id == 'default:10.0.200.5'
        assert link.remote.interface.dd_id == 'default:10.0.200.5:cisco-aci-eth5/1'
