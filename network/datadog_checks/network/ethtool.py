# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

try:
    import fcntl
except ImportError:
    fcntl = None

import array
import struct
from collections import defaultdict

from six import PY3

from .const import (
    ENA_METRIC_NAMES,
    ENA_METRIC_PREFIX,
    ETH_GSTRING_LEN,
    ETH_SS_STATS,
    ETHTOOL_GDRVINFO,
    ETHTOOL_GLOBAL_METRIC_NAMES,
    ETHTOOL_GSSET_INFO,
    ETHTOOL_GSTATS,
    ETHTOOL_GSTRINGS,
    ETHTOOL_METRIC_NAMES,
    SIOCETHTOOL,
)


def _send_ethtool_ioctl(iface, sckt, data):
    """
    Send an ioctl SIOCETHTOOL call for given interface with given data.
    """
    ifr = struct.pack('16sP', iface.encode('utf-8'), data.buffer_info()[0])
    fcntl.ioctl(sckt.fileno(), SIOCETHTOOL, ifr)


def _byte_array_to_string(s):
    """
    Convert a byte array to string
    b'hv_netvsc\x00\x00\x00\x00' -> 'hv_netvsc'
    """
    s = s.tobytes() if PY3 else s.tostring()
    s = s.partition(b'\x00')[0].decode('utf-8')
    return s


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
        s = _byte_array_to_string(strings[offset : offset + ETH_GSTRING_LEN])
        all_names.append(s)
    return all_names


def get_ethtool_drvinfo(iface, sckt):
    drvinfo = array.array('B', struct.pack('I', ETHTOOL_GDRVINFO))
    # Struct in
    # https://github.com/torvalds/linux/blob/448f413a8bdc727d25d9a786ccbdb974fb85d973/include/uapi/linux/ethtool.h#L187-L200
    # Total size: 196
    # Same result as printf("%zu\n", sizeof(struct ethtool_drvinfo));
    drvinfo.extend([0] * (4 + 32 + 32 + 32 + 32 + 32 + 12 + 5 * 4))
    _send_ethtool_ioctl(iface, sckt, drvinfo)
    driver_name = _byte_array_to_string(drvinfo[4 : 4 + 32])
    driver_version = _byte_array_to_string(drvinfo[4 + 32 : 32 + 32])
    return driver_name, driver_version


def get_ethtool_stats(iface, sckt):
    stats_names = list(_get_ethtool_gstringset(iface, sckt))
    stats_count = len(stats_names)

    stats = array.array('B', struct.pack('II', ETHTOOL_GSTATS, stats_count))
    # we need `stats_count * (length of uint64)` for the result
    stats.extend([0] * len(struct.pack('Q', 0)) * stats_count)
    _send_ethtool_ioctl(iface, sckt, stats)
    return stats_names, stats


def _parse_ethtool_queue_num(stat_name):
    """
    Extract the queue and the metric name from ethtool stat name:
    queue_0_tx_cnt -> (queue:0, tx_cnt)
    tx_queue_0_bytes -> (queue:0, tx_bytes)
    """
    if 'queue_' not in stat_name:
        return None, None
    parts = stat_name.split('_')
    if 'queue' not in parts:
        return None, None
    queue_index = parts.index('queue')
    queue_num = parts[queue_index + 1]
    if not queue_num.isdigit():
        return None, None
    parts.pop(queue_index)
    parts.pop(queue_index)
    return 'queue:{}'.format(queue_num), '_'.join(parts)


def _parse_ethtool_queue_array(stat_name):
    """
    Extract the queue and the metric name from ethtool stat name:
    tx_stop[0] -> (queue:0, tx_stop)
    """
    if '[' not in stat_name or not stat_name.endswith(']'):
        return None, None
    parts = stat_name.split('[')
    if len(parts) != 2:
        return None, None
    metric_name = parts[0]
    queue_num = parts[1][:-1]
    if not queue_num.isdigit():
        return None, None
    return 'queue:{}'.format(queue_num), metric_name


def _parse_ethtool_cpu_num(stat_name):
    """
    Extract the cpu and the metric name from ethtool stat name:
    cpu0_rx_bytes -> (cpu:0, rx_bytes)
    """
    if not stat_name.startswith('cpu'):
        return None, None
    parts = stat_name.split('_')
    cpu_num = parts[0][3:]
    if not cpu_num.isdigit():
        return None, None
    parts.pop(0)
    return 'cpu:{}'.format(cpu_num), '_'.join(parts)


def _get_stat_value(stats, index):
    offset = 8 + 8 * index
    value = struct.unpack('Q', stats[offset : offset + 8])[0]
    return value


def get_ethtool_metrics(driver_name, stats_names, stats):
    """
    Get all ethtool metrics specified in ETHTOOL_METRIC_NAMES list and their values from ethtool.
    We convert the queue and cpu number to a tag: queue_0_tx_cnt will be submitted as tx_cnt with the tag queue:0

    Return [tag][metric] -> value
    """
    res = defaultdict(dict)
    if driver_name not in ETHTOOL_METRIC_NAMES:
        return res
    ethtool_global_metrics = ETHTOOL_GLOBAL_METRIC_NAMES.get(driver_name, {})
    for i, stat_name in enumerate(stats_names):
        tag, metric_name = _parse_ethtool_queue_num(stat_name)
        metric_prefix = '.queue.'
        if not tag:
            tag, metric_name = _parse_ethtool_cpu_num(stat_name)
            metric_prefix = '.cpu.'
        if not tag:
            tag, metric_name = _parse_ethtool_queue_array(stat_name)
            metric_prefix = '.queue.'
        if metric_name and metric_name not in ETHTOOL_METRIC_NAMES[driver_name]:
            # A per queue/cpu metric was found but is not part of the collected metrics
            continue
        if not tag and stat_name in ethtool_global_metrics:
            tag = 'global'
            metric_prefix = '.'
            metric_name = stat_name
        if not tag:
            continue
        res[tag][driver_name + metric_prefix + metric_name] = _get_stat_value(stats, i)
    return res


def get_ena_metrics(stats_names, stats):
    """
    Get all ENA metrics specified in ENA_METRICS_NAMES list and their values from ethtool.
    """
    metrics = {}
    for i, stat_name in enumerate(stats_names):
        if stat_name in ENA_METRIC_NAMES:
            metrics[ENA_METRIC_PREFIX + stat_name] = _get_stat_value(stats, i)
    return metrics
