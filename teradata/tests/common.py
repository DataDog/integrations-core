# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from copy import deepcopy

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_here
from datadog_checks.dev.ci import running_on_ci

HERE = get_here()
CHECK_NAME = 'teradata'
ON_CI = running_on_ci()

TERADATA_SERVER = os.environ.get('TERADATA_SERVER')
TERADATA_DD_USER = os.environ.get('TERADATA_DD_USER')
TERADATA_DD_PW = os.environ.get('TERADATA_DD_PW')
USE_TD_SANDBOX = is_affirmative(os.environ.get('USE_TD_SANDBOX'))

TABLE_EXTRACTION_PATTERN = re.compile(r'SELECT .* FROM \w+\.(\w+)')

SERVICE_CHECK_CONNECT = 'teradata.can_connect'
SERVICE_CHECK_QUERY = 'teradata.can_query'

EXPECTED_TAGS = ['teradata_server:tdserver', 'teradata_port:1025', 'td_env:dev']

CONFIG = {
    'server': 'tdserver',
    'username': 'datadog',
    'password': 'td_datadog',
    'database': 'AdventureWorksDW',
    'collect_res_usage_metrics': True,
    'collect_table_disk_metrics': True,
    'tags': ['td_env:dev'],
}

E2E_CONFIG = {
    'server': TERADATA_SERVER,
    'username': TERADATA_DD_USER,
    'password': TERADATA_DD_PW,
    'database': 'AdventureWorksDW',
    'collect_res_usage_metrics': True,
    'collect_table_disk_metrics': True,
}

E2E_METADATA = {
    'start_commands': [
        'pip install teradatasql',
    ]
}

DEFAULT_METRICS = [
    'teradata.disk_space.max_perm.total',
    'teradata.disk_space.max_spool.total',
    'teradata.disk_space.max_temp.total',
    'teradata.disk_space.curr_perm.total',
    'teradata.disk_space.curr_spool.total',
    'teradata.disk_space.curr_persist_spool.total',
    'teradata.disk_space.curr_temp.total',
    'teradata.disk_space.peak_perm.total',
    'teradata.disk_space.peak_spool.total',
    'teradata.disk_space.peak_persist_spool.total',
    'teradata.disk_space.peak_temp.total',
    'teradata.disk_space.max_prof_spool.total',
    'teradata.disk_space.max_prof_temp.total',
    'teradata.disk_space.alloc_perm.total',
    'teradata.disk_space.alloc_spool.total',
    'teradata.disk_space.alloc_temp.total',
    'teradata.disk_space.perm_skew.total',
    'teradata.disk_space.spool_skew.total',
    'teradata.disk_space.temp_skew.total',
    'teradata.amp.cpu_time',
    'teradata.amp.disk_io',
    'teradata.amp.cpu_time_norm',
]

RES_USAGE_METRICS = [
    'teradata.file_lock.blocks',
    'teradata.file_lock.deadlocks',
    'teradata.file_lock.enters',
    'teradata.db_lock.blocks',
    'teradata.db_lock.deadlocks',
    'teradata.io.throttle_count',
    'teradata.io.throttle_time',
    'teradata.io.throttle_time_max',
    'teradata.mem.ctxt_page_reads',
    'teradata.mem.ctxt_page_writes',
    'teradata.mem.txt_page_reads',
    'teradata.mem.vh_cache_size',
    'teradata.mem.kernel_inuse_size',
    'teradata.mem.seg_mdl.inuse_size',
    'teradata.mem.seg_max_avail_size',
    'teradata.mem.seg_in_use_size',
    'teradata.mem.seg_cache_size',
    'teradata.mem.seg_mdl.alloc',
    'teradata.mem.seg_mdl.free',
    'teradata.mem.seg_mdl.release',
    'teradata.mem.seg_mdl.recycle',
    'teradata.mem.seg_mdl.alloc_size',
    'teradata.mem.seg_mdl.free_size',
    'teradata.mem.seg_mdl.release_size',
    'teradata.mem.seg_mdl.recycle_size',
    'teradata.mem.fsg.cache_size',
    'teradata.mem.page_faults_major',
    'teradata.mem.page_faults_minor',
    'teradata.process.blocked',
    'teradata.process.ready',
    'teradata.process.ready_max',
    'teradata.process.cpu_idle',
    'teradata.process.cpu_io_wait',
    'teradata.process.cpu_serv',
    'teradata.process.cpu_exec',
    'teradata.process.cpu_throttle',
    'teradata.process.cpu_throttle_time',
]

TABLE_DISK_METRICS = [
    'teradata.disk_space.max_perm',
    'teradata.disk_space.max_spool',
    'teradata.disk_space.max_temp',
    'teradata.disk_space.curr_perm',
    'teradata.disk_space.curr_spool',
    'teradata.disk_space.curr_persist_spool',
    'teradata.disk_space.curr_temp',
    'teradata.disk_space.peak_perm',
    'teradata.disk_space.peak_spool',
    'teradata.disk_space.peak_persist_spool',
    'teradata.disk_space.peak_temp',
    'teradata.disk_space.max_prof_spool',
    'teradata.disk_space.max_prof_temp',
    'teradata.disk_space.alloc_perm',
    'teradata.disk_space.alloc_spool',
    'teradata.disk_space.alloc_temp',
    'teradata.disk_space.perm_skew',
    'teradata.disk_space.spool_skew',
    'teradata.disk_space.temp_skew',
]

E2E_EXCLUDE_METRICS = [
    'teradata.disk_space.max_prof_spool.total',
    'teradata.disk_space.max_prof_temp.total',
]

EXPECTED_METRICS = deepcopy(DEFAULT_METRICS)
EXPECTED_METRICS += RES_USAGE_METRICS + TABLE_DISK_METRICS
