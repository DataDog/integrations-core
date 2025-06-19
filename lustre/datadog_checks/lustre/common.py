# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

IGNORED_JOBSTATS_METRICS = [
    'job_id',
    'snapshot_time',
    'start_time',
    'elapsed_time',
]

LCTL_PATH = '/usr/sbin/lctl'
LNETCTL_PATH = '/usr/sbin/lnetctl'

OSS_JOBSTATS_PARAM_REGEX = 'ost.*.job_stats'
MDS_JOBSTATS_PARAM_REGEX = 'obdfilter.*.job_stats'