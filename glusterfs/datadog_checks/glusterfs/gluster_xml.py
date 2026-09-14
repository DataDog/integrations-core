# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Parse the native ``gluster --xml`` output into the dict shape the check submits.

This module talks to the ``gluster`` CLI directly and replaces the vendored
``gstatus``/``glustercli``/``glusterlib`` stack. It depends only on the Python
standard library and the ``gluster`` binary being present on the host (a
prerequisite of the ``glusterfs-server`` package, which the integration already
requires).

The XML schema parsed here is Gluster's own documented ``--xml`` output format;
the parsing implementation is original and does not derive from the upstream
GPL-licensed ``gstatus`` sources.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from typing import Any

__all__ = [
    'GlusterXMLError',
    'parse_volume_info',
    'parse_volume_status',
    'parse_heal_info',
    'parse_pool_list',
    'parse_gluster_version',
    'build_cluster_data',
]

# Volume states (from ``gluster volume info`` ``statusStr``).
STATE_STARTED = 'Started'

# Volume / subvolume types (``typeStr`` upper-cased, ``-`` -> ``_``).
TYPE_REPLICATE = 'REPLICATE'
TYPE_DISPERSE = 'DISPERSE'

# Health states consumed by the check's service checks.
HEALTH_UP = 'up'
HEALTH_DOWN = 'down'
HEALTH_PARTIAL = 'partial'
HEALTH_DEGRADED = 'degraded'

CLUSTER_HEALTHY = 'Healthy'
CLUSTER_DEGRADED = 'Degraded'


class GlusterXMLError(Exception):
    """Raised when ``gluster --xml`` output cannot be parsed or reports an error."""


def _text(element: ET.Element, key: str, default: str | None = None) -> str | None:
    child = element.find(key)
    if child is None or child.text is None:
        return default
    return child.text


def _int(element: ET.Element, key: str, default: int = 0) -> int:
    value = _text(element, key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as e:
        raise GlusterXMLError(f'Expected integer for <{key}>, got {value!r}') from e


def _check_op_ret(root: ET.Element) -> None:
    """Raise if the CLI reported a failure inside an otherwise well-formed XML envelope.

    ``gluster --xml`` returns exit 0 and emits valid XML even when the underlying
    command failed; the failure is signalled by ``<opRet>-1</opRet>``.
    """
    op_ret = _text(root, 'opRet')
    if op_ret is not None and op_ret.strip() == '-1':
        op_err = _text(root, 'opErrstr', 'gluster command failed') or 'gluster command failed'
        raise GlusterXMLError(op_err)


def _transport_str(value: str | None) -> str:
    if value == '0':
        return 'TCP'
    if value == '1':
        return 'RDMA'
    return 'TCP,RDMA'


def _parse_a_volume(volume_el: ET.Element) -> dict[str, Any]:
    name = _text(volume_el, 'name')
    if name is None:
        raise GlusterXMLError('volume element is missing <name>')

    type_str = _text(volume_el, 'typeStr', '')
    # Normalise to the upper-case, underscore form the check expects (e.g.
    # "Distributed-Replicate" -> "DISTRIBUTED_REPLICATE").
    type_str = type_str.upper().replace('-', '_')

    bricks: list[dict[str, Any]] = []
    for brick in volume_el.findall('bricks/brick'):
        brick_name = _text(brick, 'name')
        if brick_name is None:
            raise GlusterXMLError('brick element is missing <name>')
        brick_type = 'Arbiter' if _text(brick, 'isArbiter') == '1' else 'Brick'
        bricks.append(
            {
                'name': brick_name,
                'uuid': _text(brick, 'hostUuid', ''),
                'type': brick_type,
            }
        )

    options = [
        {'name': _text(opt, 'name', ''), 'value': _text(opt, 'value', '')}
        for opt in volume_el.findall('options/option')
    ]

    return {
        'name': name,
        'uuid': _text(volume_el, 'id', ''),
        'type': type_str,
        'status': _text(volume_el, 'statusStr', ''),
        'num_bricks': _int(volume_el, 'brickCount'),
        'distribute': _int(volume_el, 'distCount', 1),
        'replica': _int(volume_el, 'replicaCount', 1),
        'disperse': _int(volume_el, 'disperseCount', 0),
        'disperse_redundancy': _int(volume_el, 'redundancyCount', 0),
        'transport': _transport_str(_text(volume_el, 'transport', '0')),
        'snapshot_count': _int(volume_el, 'snapshotCount'),
        'bricks': bricks,
        'options': options,
    }


def parse_volume_info(xml_text: str) -> list[dict[str, Any]]:
    """Parse ``gluster --xml volume info`` into a list of volume dicts.

    Each volume carries its brick list (name/uuid/type) and option list; per-brick
    runtime status (online, sizes, inodes) is merged in by
    :func:`parse_volume_status`.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise GlusterXMLError(f'volume info XML is not well-formed: {e}') from e
    _check_op_ret(root)

    volumes: list[dict[str, Any]] = []
    for volume_el in root.findall('volInfo/volumes/volume'):
        volumes.append(_parse_a_volume(volume_el))
    return volumes


def _parse_a_node(node_el: ET.Element) -> dict[str, Any]:
    hostname = _text(node_el, 'hostname')
    path = _text(node_el, 'path')
    if hostname is None or path is None:
        raise GlusterXMLError('status node is missing hostname/path')
    name = f'{hostname}:{path}'

    online = _text(node_el, 'status') == '1'
    if not online:
        # No point reading the rest; the caller falls back to default values.
        return {'name': name, 'online': False}

    size_total = _int(node_el, 'sizeTotal', 0)
    size_free = _int(node_el, 'sizeFree', 0)
    inodes_total = _int(node_el, 'inodesTotal', 0)
    inodes_free = _int(node_el, 'inodesFree', 0)
    return {
        'name': name,
        'uuid': _text(node_el, 'peerid', ''),
        'online': True,
        'pid': _text(node_el, 'pid', '-1'),
        'size_total': size_total,
        'size_free': size_free,
        'size_used': size_total - size_free,
        'inodes_total': inodes_total,
        'inodes_free': inodes_free,
        'inodes_used': inodes_total - inodes_free,
        'device': _text(node_el, 'device', 'N/A'),
        'block_size': _text(node_el, 'blockSize', 'N/A'),
        'mnt_options': _text(node_el, 'mntOptions', 'N/A'),
        'fs_name': _text(node_el, 'fsName', 'N/A'),
    }


def _default_brick(brick: dict[str, Any]) -> dict[str, Any]:
    """A brick's status when it is offline or absent from ``volume status``."""
    return {
        'name': brick['name'],
        'uuid': brick['uuid'],
        'type': brick['type'],
        'online': False,
        'pid': 'N/A',
        'size_total': 0,
        'size_free': 0,
        'size_used': 0,
        'inodes_total': 0,
        'inodes_free': 0,
        'inodes_used': 0,
        'device': 'N/A',
        'block_size': 'N/A',
        'mnt_options': 'N/A',
        'fs_name': 'N/A',
    }


def _subvol_brick_count(replica: int, disperse: int) -> int:
    if replica > 1:
        return replica
    if disperse > 0:
        return disperse
    return 1


def _group_subvols(volumes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Split each volume's flat brick list into subvolumes based on replica/disperse counts."""
    out: list[dict[str, Any]] = []
    for vol in volumes:
        subvol_type = vol['type'].split('_')[-1] if vol['type'] else ''
        bricks_per_subvol = _subvol_brick_count(vol['replica'], vol['disperse'])
        num_subvols = len(vol['bricks']) // bricks_per_subvol if bricks_per_subvol else 0

        subvols: list[dict[str, Any]] = []
        for sidx in range(num_subvols):
            start = sidx * bricks_per_subvol
            subvols.append(
                {
                    'name': f"{vol['name']}-{subvol_type.lower()}-{sidx}",
                    'replica': vol['replica'],
                    'disperse': vol['disperse'],
                    'disperse_redundancy': vol['disperse_redundancy'],
                    'type': subvol_type,
                    'bricks': vol['bricks'][start : start + bricks_per_subvol],
                }
            )
        copied = dict(vol)
        copied['bricks'] = []
        copied['subvols'] = subvols
        out.append(copied)
    return out


def _subvol_health(subvol: dict[str, Any]) -> str:
    up_bricks = sum(1 for brick in subvol['bricks'] if brick['online'])
    if up_bricks == len(subvol['bricks']):
        return HEALTH_UP

    if subvol['type'] == TYPE_REPLICATE and up_bricks >= math.ceil(subvol['replica'] / 2):
        return HEALTH_PARTIAL

    if subvol['type'] == TYPE_DISPERSE:
        down_bricks = len(subvol['bricks']) - up_bricks
        if down_bricks <= subvol['disperse_redundancy']:
            return HEALTH_PARTIAL

    return HEALTH_DOWN


def _update_volume_health(volumes: list[dict[str, Any]]) -> None:
    for vol in volumes:
        if vol['status'] != STATE_STARTED:
            continue

        vol['health'] = HEALTH_UP
        up_subvols = 0
        for subvol in vol['subvols']:
            subvol['health'] = _subvol_health(subvol)
            if subvol['health'] == HEALTH_DOWN:
                vol['health'] = HEALTH_DEGRADED
            elif subvol['health'] == HEALTH_PARTIAL and vol['health'] != HEALTH_DEGRADED:
                vol['health'] = HEALTH_PARTIAL
            if subvol['health'] != HEALTH_DOWN:
                up_subvols += 1
        if up_subvols == 0:
            vol['health'] = HEALTH_DOWN


def _update_volume_utilization(volumes: list[dict[str, Any]]) -> None:
    """Aggregate per-brick capacity/inodes into per-volume and per-subvolume totals.

    For replicate/arbiter subvols the effective capacity is the max used and the
    min total across the non-arbiter bricks (mirrors report the same data, so we
    take the representative brick). For disperse subvols the data bricks share
    the load, so the effective capacity is scaled by the data-brick count
    (``disperse - disperse_redundancy``).
    """
    for vol in volumes:
        vol['size_total'] = 0
        vol['size_free'] = 0
        vol['size_used'] = 0
        vol['inodes_total'] = 0
        vol['inodes_free'] = 0
        vol['inodes_used'] = 0

        for subvol in vol['subvols']:
            eff_used = 0
            eff_total = 0
            eff_inodes_used = 0
            eff_inodes_total = 0

            for brick in subvol['bricks']:
                if brick['type'] == 'Arbiter':
                    continue

                eff_used = max(eff_used, brick['size_used'])
                if eff_total == 0 or (brick['size_total'] <= eff_total and brick['size_total'] > 0):
                    eff_total = brick['size_total']

                eff_inodes_used = max(eff_inodes_used, brick['inodes_used'])
                if eff_inodes_total == 0 or (brick['inodes_total'] <= eff_inodes_total and brick['inodes_total'] > 0):
                    eff_inodes_total = brick['inodes_total']

            if subvol['type'] == TYPE_DISPERSE:
                data_bricks = subvol['disperse'] - subvol['disperse_redundancy']
                eff_used *= data_bricks
                eff_total *= data_bricks
                eff_inodes_used *= data_bricks
                eff_inodes_total *= data_bricks

            vol['size_total'] += eff_total
            vol['size_used'] += eff_used
            vol['inodes_total'] += eff_inodes_total
            vol['inodes_used'] += eff_inodes_used

        vol['size_free'] = vol['size_total'] - vol['size_used']
        vol['inodes_free'] = vol['inodes_total'] - vol['inodes_used']

        online = sum(1 for subvol in vol['subvols'] for brick in subvol['bricks'] if brick['online'])
        vol['online'] = online

        if vol['size_total'] > 0:
            vol['used_percent'] = round((vol['size_used'] / vol['size_total']) * 100, 2)
        else:
            vol['used_percent'] = 0.0


def parse_volume_status(xml_text: str, volinfo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse ``gluster --xml volume status all detail`` and merge it into ``volinfo``.

    Returns one volume dict per volume in ``volinfo`` with subvols grouped and
    per-volume utilization/health computed. Bricks that are offline or absent
    from the status output are filled with zeroed default values.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise GlusterXMLError(f'volume status XML is not well-formed: {e}') from e
    _check_op_ret(root)

    # Index every reported node by "hostname:path" so we can look up each brick
    # from volume info. Non-brick nodes (daemons) simply never match a brick.
    status_by_name: dict[str, dict[str, Any]] = {}
    for node_el in root.findall('volStatus/volumes/volume/node'):
        node = _parse_a_node(node_el)
        status_by_name[node['name']] = node

    volumes: list[dict[str, Any]] = []
    for vol in volinfo:
        merged = dict(vol)
        merged['bricks'] = []
        for brick in vol['bricks']:
            status = status_by_name.get(brick['name'])
            if status is None or not status.get('online', False):
                merged['bricks'].append(_default_brick(brick))
            else:
                brick_status = dict(status)
                # Preserve the Brick/Arbiter type from volume info.
                brick_status['type'] = brick['type']
                merged['bricks'].append(brick_status)
        volumes.append(merged)

    grouped = _group_subvols(volumes)
    _update_volume_utilization(grouped)
    _update_volume_health(grouped)
    return grouped


def parse_heal_info(xml_text: str) -> list[dict[str, Any]]:
    """Parse ``gluster --xml volume heal <vol> info`` into per-brick heal entries."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise GlusterXMLError(f'heal info XML is not well-formed: {e}') from e
    _check_op_ret(root)

    healinfo: list[dict[str, Any]] = []
    for brick_el in root.findall('healInfo/bricks/brick'):
        healinfo.append(
            {
                'name': _text(brick_el, 'name', ''),
                'status': _text(brick_el, 'status', ''),
                'host_uuid': brick_el.attrib.get('hostUuid', ''),
                'nr_entries': _text(brick_el, 'numberOfEntries', '-'),
            }
        )
    return healinfo


def _parse_a_peer(peer_el: ET.Element) -> dict[str, Any]:
    connected = _text(peer_el, 'connected', '0')
    if connected == '0':
        connected = 'Disconnected'
    elif connected == '1':
        connected = 'Connected'
    return {
        'uuid': _text(peer_el, 'uuid', ''),
        'hostname': _text(peer_el, 'hostname', ''),
        'connected': connected,
    }


def parse_pool_list(xml_text: str) -> list[dict[str, Any]]:
    """Parse ``gluster --xml pool list`` into the cluster peer list (including self)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise GlusterXMLError(f'pool list XML is not well-formed: {e}') from e
    _check_op_ret(root)

    peers: list[dict[str, Any]] = []
    for peer_el in root.findall('peerStatus/peer'):
        peers.append(_parse_a_peer(peer_el))
    return peers


def parse_gluster_version(version_text: str) -> str:
    """Extract the GlusterFS version from ``gluster --version`` output.

    The first line looks like ``glusterfs 10.1`` — the second whitespace-delimited
    token is the version string the check submits as metadata.
    """
    first_line = version_text.splitlines()[0] if version_text.strip() else ''
    parts = first_line.split()
    if len(parts) < 2:
        raise GlusterXMLError(f'could not parse gluster version from: {version_text!r}')
    return parts[1]


def build_cluster_data(
    volumes: list[dict[str, Any]],
    peers: list[dict[str, Any]],
    glusterfs_version: str,
) -> dict[str, Any]:
    """Assemble the cluster-level dict the check submits to ``metrics.py``."""
    node_count = len(peers)
    nodes_active = sum(1 for peer in peers if peer['connected'] == 'Connected')
    cluster_status = CLUSTER_HEALTHY if nodes_active >= node_count else CLUSTER_DEGRADED

    volume_count = len(volumes)
    volumes_started = sum(1 for vol in volumes if vol['status'] == STATE_STARTED)

    return {
        'cluster_status': cluster_status,
        'glfs_version': glusterfs_version,
        'node_count': node_count,
        'nodes_active': nodes_active,
        'volume_count': volume_count,
        'volumes_started': volumes_started,
        'volume_summary': volumes,
    }
