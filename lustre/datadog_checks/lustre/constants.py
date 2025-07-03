# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass

FILESYSTEM_DISCOVERY_PARAM_MAPPING = {
    'mds': (r'mdt.*.job_stats', r'(?<=mdt\.).*(?=-MDT)'),
    'oss': (r'obdfilter.*.job_stats', r'(?<=obdfilter\.).*(?=-OST)'),
    'client': (r'llite.*.stats', r'(?<=llite\.).*(?=-[^-]*\.stats)'),
}

IGNORED_STATS = {
    'snapshot_time',
    'start_time',
    'elapsed_time',
}

IGNORED_LNET_GROUPS = {
    'interfaces',
}


@dataclass(frozen=True)
class LustreParam:
    regex: str
    node_types: tuple[str, ...]
    wildcards: tuple[str, ...] = ()
    prefix: str = ''
    fixture: str = ''


JOBSTATS_PARAMS = [
    LustreParam(
        regex=r'obdfilter.*.job_stats',
        node_types=('oss',),
        wildcards=('device_name',),
        prefix='job_stats',
        fixture='oss_jobstats.txt',
    ),
    LustreParam(
        regex=r'mdt.*.job_stats',
        node_types=('mds',),
        wildcards=('device_name',),
        prefix='job_stats',
        fixture='mds_jobstats.txt',
    ),
]


DEFAULT_PARAMS = [
    LustreParam(
        regex='llite.*.stats',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='client_llite_stats.txt',
    ),
]

EXTRA_PARAMS = [
    # MDS (Metadata Server) params
    LustreParam(regex='mds.MDS.mdt.stats', node_types=('mds',), prefix='mds.mdt', fixture='mds_mdt_stats.txt'),
    LustreParam(
        regex='mdt.*.exports.*.stats',
        node_types=('mds',),
        wildcards=('device_name', 'nid'),
        prefix='mds.mdt.exports',
        fixture='mds_mdt_export_stats.txt',
    ),
    # Client params
    LustreParam(
        regex='mdc.*.stats',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='mdc',
        fixture='client_mdc_stats.txt',
    ),
    # LDLM (Lustre Distributed Lock Manager) params
    LustreParam(
        regex='ldlm.services.*.stats',
        node_types=('client', 'mds', 'oss'),
        wildcards=('ldlm_service',),
        prefix='ldlm.services',
        fixture='all_ldlm_services_stats.txt',
    ),
    LustreParam(
        regex='ldlm.namespaces.*.pool.stats',
        node_types=('client', 'mds', 'oss'),
        wildcards=('device_uuid',),
        prefix='ldlm.namespaces.pool',
        fixture='all_ldlm_namespace_stats.txt',
    ),
    # MGS (Management Server) params
    LustreParam(
        regex='mgs.MGS.exports.*.stats',
        node_types=('mds',),
        wildcards=('device_name', 'nid'),
        prefix='mgs.exports',
        fixture='mds_mgs_export_stats.txt',
    ),
    # OSS (Object Storage Server) params
    LustreParam(regex='ost.OSS.oss.stats', node_types=('oss',), prefix='ost.oss', fixture='oss_ost_stats.txt'),
    LustreParam(
        regex='osc.*.stats',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='osc',
        fixture='client_osc_stats.txt',
    ),
    LustreParam(
        regex='obdfilter.*.exports.*.stats',
        node_types=('oss',),
        wildcards=('device_name', 'nid'),
        prefix='obdfilter.exports',
        fixture='oss_obdfilter_export_stats.txt',
    ),
    LustreParam(
        regex='obdfilter.*.stats',
        node_types=('oss',),
        wildcards=('device_name',),
        prefix='obdfilter',
        fixture='oss_obdfilter_stats.txt',
    ),
]
