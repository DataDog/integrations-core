# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass
from typing import Tuple

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

TAGS_WITH_FILESYSTEM = {
    'device_name',
    'device_uuid',
}


@dataclass(frozen=True)
class LustreParam:
    regex: str
    node_types: Tuple[str, ...]
    wildcards: Tuple[str, ...] = ()
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

JOBID_TAG_PARAMS = [
    LustreParam(
        regex=r'jobid_var',
        node_types=(
            'client',
            'mds',
            'oss',
        ),
        fixture='disable',
    ),
    LustreParam(
        regex=r'jobid_name',
        node_types=(
            'client',
            'mds',
            'oss',
        ),
        fixture='%e.%u',
    ),
]

CURATED_PARAMS = [
    LustreParam(
        regex=r'osd-*.*.blocksize',
        node_types=('mds', 'oss'),
        wildcards=('device_name',),
        prefix='osd',
        fixture='4096',
    ),
    LustreParam(
        regex=r'osd-*.*.filesfree',
        node_types=('mds', 'oss'),
        wildcards=('device_name',),
        prefix='osd',
        fixture='41942760',
    ),
    LustreParam(
        regex=r'osd-*.*.filestotal',
        node_types=('mds', 'oss'),
        wildcards=('device_name',),
        prefix='osd',
        fixture='41943040',
    ),
    LustreParam(
        regex=r'osd-*.*.kbytesavail',
        node_types=('mds', 'oss'),
        wildcards=('device_name',),
        prefix='osd',
        fixture='52941060',
    ),
    LustreParam(
        regex=r'osd-*.*.kbytesfree',
        node_types=('mds', 'oss'),
        wildcards=('device_name',),
        prefix='osd',
        fixture='58183936',
    ),
    LustreParam(
        regex=r'osd-*.*.kbytestotal',
        node_types=('mds', 'oss'),
        wildcards=('device_name',),
        prefix='osd',
        fixture='58189732',
    ),
    LustreParam(
        regex=r'llite.*.blocksize',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='4096',
    ),
    LustreParam(
        regex=r'llite.*.checksum_pages',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='1',
    ),
    LustreParam(
        regex=r'llite.*.default_easize',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='128',
    ),
    LustreParam(
        regex=r'llite.*.enable_filename_encryption',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='0',
    ),
    LustreParam(
        regex=r'llite.*.enable_setstripe_gid',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='-1',
    ),
    LustreParam(
        regex=r'llite.*.enable_statahead_fname',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='0',
    ),
    LustreParam(
        regex=r'llite.*.fast_read',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='1',
    ),
    LustreParam(
        regex=r'llite.*.file_heat',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='0',
    ),
    LustreParam(
        regex=r'llite.*.filename_enc_use_old_base64',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='0',
    ),
    LustreParam(
        regex=r'llite.*.filesfree',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='1542098',
    ),
    LustreParam(
        regex=r'llite.*.filestotal',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='1542378',
    ),
    LustreParam(
        regex=r'llite.*.hybrid_io_read_threshold_bytes',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='8388608',
    ),
    LustreParam(
        regex=r'llite.*.hybrid_io_write_threshold_bytes',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='2097152',
    ),
    LustreParam(
        regex=r'llite.*.inode_cache',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='1',
    ),
    LustreParam(
        regex=r'llite.*.intent_mkdir',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='0',
    ),
    LustreParam(
        regex=r'llite.*.kbytesavail',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='96904844',
    ),
    LustreParam(
        regex=r'llite.*.kbytesfree',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='102164108',
    ),
    LustreParam(
        regex=r'llite.*.kbytestotal',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='102165532',
    ),
    LustreParam(
        regex=r'llite.*.lazystatfs',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='1',
    ),
    LustreParam(
        regex=r'llite.*.max_easize',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='65536',
    ),
    LustreParam(
        regex=r'llite.*.max_read_ahead_mb',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='256',
    ),
    LustreParam(
        regex=r'llite.*.max_read_ahead_per_file_mb',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='64',
    ),
    LustreParam(
        regex=r'llite.*.max_read_ahead_whole_mb',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='64',
    ),
    LustreParam(
        regex=r'llite.*.statahead_agl',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='1',
    ),
    LustreParam(
        regex=r'llite.*.statahead_max',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='128',
    ),
]


DEFAULT_STATS = [
    LustreParam(
        regex='llite.*.stats',
        node_types=('client',),
        wildcards=('device_uuid',),
        prefix='filesystem',
        fixture='client_llite_stats.txt',
    ),
]

EXTRA_STATS = [
    # MDS (Metadata Server) params
    LustreParam(
        regex='mds.MDS.mdt.stats',
        node_types=('mds',),
        prefix='mds.mdt',
        fixture='mds_mdt_stats.txt',
    ),
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
        wildcards=('nid',),
        prefix='ldlm.namespaces.pool',
        fixture='all_ldlm_namespace_stats.txt',
    ),
    # MGS (Management Server) params
    LustreParam(
        regex='mgs.MGS.exports.*.stats',
        node_types=('mds',),
        wildcards=('nid',),
        prefix='mgs.exports',
        fixture='mds_mgs_export_stats.txt',
    ),
    # OSS (Object Storage Server) params
    LustreParam(
        regex='ost.OSS.ost.stats',
        node_types=('oss',),
        prefix='oss',
        fixture='oss_ost_stats.txt',
    ),
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
