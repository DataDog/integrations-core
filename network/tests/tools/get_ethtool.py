# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import array
import fcntl
import socket
import struct
import sys

SIOCETHTOOL = 0x8946
ETHTOOL_GSTRINGS = 0x0000001B
ETHTOOL_GSSET_INFO = 0x00000037
ETHTOOL_GSTATS = 0x0000001D
ETHTOOL_GDRVINFO = 0x00000003
ETH_SS_STATS = 0x1
ETH_GSTRING_LEN = 32


def _send_ethtool_ioctl(iface, sckt, data):
    """
    Send an ioctl SIOCETHTOOL call for given interface with given data.
    """
    print('("{}", {}):'.format(iface, data.tobytes()))
    ifr = struct.pack('16sP', iface.encode('utf-8'), data.buffer_info()[0])
    fcntl.ioctl(sckt.fileno(), SIOCETHTOOL, ifr)
    print('{},'.format(data.tobytes()))


def _get_ethtool_gstringset(iface, sckt):
    """
    Retrieve names of all ethtool stats for given interface.
    """
    sset_info = array.array('B', struct.pack('IIQI', ETHTOOL_GSSET_INFO, 0, 1 << ETH_SS_STATS, 0))
    _send_ethtool_ioctl(iface, sckt, sset_info)
    sset_mask, sset_len = struct.unpack('8xQI', sset_info)
    if sset_mask == 0:
        sset_len = 0
    strings = array.array('B', struct.pack('III', ETHTOOL_GSTRINGS, ETH_SS_STATS, sset_len))
    strings.extend([0] * sset_len * ETH_GSTRING_LEN)
    _send_ethtool_ioctl(iface, sckt, strings)

    all_names = []
    for i in range(sset_len):
        offset = 12 + ETH_GSTRING_LEN * i
        name = strings[offset : offset + ETH_GSTRING_LEN]
        name = name.tobytes()
        name = name.partition(b'\x00')[0].decode('utf-8')
        all_names.append(name)
    return all_names


def get_ethtool_drvinfo(iface, sckt):
    drvinfo = array.array('B', struct.pack('I', ETHTOOL_GDRVINFO))
    drvinfo.extend([0] * (4 + 32 + 32 + 32 + 32 + 32 + 12 + 5 * 4))
    _send_ethtool_ioctl(iface, sckt, drvinfo)
    driver_version = drvinfo[4 + 32 : 32 + 32]
    driver_version = driver_version.tobytes()
    driver_version = driver_version.partition(b'\x00')[0].decode('utf-8')
    driver_name = drvinfo[4 : 4 + 32]
    driver_name = driver_name.tobytes()
    driver_name = driver_name.partition(b'\x00')[0].decode('utf-8')


def get_metric(iface, sckt):
    """
    Get all ENA metrics specified in ENA_METRICS_NAMES list and their values from ethtool.
    """
    stats_names = list(_get_ethtool_gstringset(iface, sckt))
    stats_count = len(stats_names)

    stats = array.array('B', struct.pack('II', ETHTOOL_GSTATS, stats_count))
    # we need `stats_count * (length of uint64)` for the result
    stats.extend([0] * len(struct.pack('Q', 0)) * stats_count)
    _send_ethtool_ioctl(iface, sckt, stats)


if len(sys.argv) != 1:
    print('Provide a single network interface name as parameter (eth0, ens5...)')
    sys.exit(1)


iface = sys.argv[1]
ethtool_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
get_ethtool_drvinfo(iface, ethtool_socket)
print()
get_metric(iface, ethtool_socket)
