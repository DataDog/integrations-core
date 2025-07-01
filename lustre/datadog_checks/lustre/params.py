# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass

@dataclass(frozen=True)
class LustreParam:
    regex: str
    node_types: tuple[str, ...]
    wildcards: tuple[str, ...] = ()
    prefix: str = ''

DEFAULT_PARAMS = [
    LustreParam(
        regex='llite.*.stats',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem'
    ),
]

EXTRA_PARAMS = [
    # MDS (Metadata Server) params
    LustreParam(
        regex='mds.MDS.mdt.stats',
        node_types=('mds',),
        prefix='mds.mdt'
    ),
    LustreParam(
        regex='mdt.*.exports.*.stats',
        node_types=('mds',),
        wildcards=('device_name', 'nid'),
        prefix='mds.mdt.exports'
    ),
    
    # Client params
    LustreParam(
        regex='mdc.*.stats',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='mdc'
    ),
    
    # LDLM (Lustre Distributed Lock Manager) params
    LustreParam(
        regex='ldlm.services.*.stats',
        node_types=('client', 'mds', 'oss'),
        wildcards=('ldlm_service',),
        prefix='ldlm.services'
    ),
    LustreParam(
        regex='ldlm.namespaces.*.pool.stats',
        node_types=('client', 'mds', 'oss'),
        wildcards=('device_uuid',),
        prefix='ldlm.namespaces.pool'
    ),
    
    # MGS (Management Server) params
    LustreParam(
        regex='mgs.MGS.exports.*.stats',
        node_types=('mds',),
        wildcards=('device_name', 'nid'),
        prefix='mgs.exports'
    ),
    
    # OSS (Object Storage Server) params
    LustreParam(
        regex='ost.OSS.oss.stats',
        node_types=('oss',),
        prefix='ost.oss'
    ),
    LustreParam(
        regex='osc.*.stats',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='osc'
    ),
    LustreParam(
        regex='obdfilter.*.exports.*.stats',
        node_types=('oss',),
        wildcards=('device_name', 'nid'),
        prefix='obdfilter.exports'
    ),
    LustreParam(
        regex='obdfilter.*.stats',
        node_types=('oss',),
        wildcards=('device_name',),
        prefix='obdfilter'
    ),
]

