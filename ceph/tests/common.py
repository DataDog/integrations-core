# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

# Constants
CHECK_NAME = 'ceph'
HERE = os.path.abspath(os.path.dirname(__file__))
FIXTURE_DIR = os.path.join(HERE, 'fixtures')

BASIC_CONFIG = {'ceph_cmd': 'docker exec dd-test-ceph ceph', 'tags': ['optional:tag1']}

EXPECTED_METRICS = [
    "ceph.commit_latency_ms",
    "ceph.apply_latency_ms",
    "ceph.op_per_sec",
    "ceph.read_bytes_sec",
    "ceph.write_bytes_sec",
    "ceph.num_osds",
    "ceph.num_in_osds",
    "ceph.num_up_osds",
    "ceph.num_pgs",
    "ceph.num_mons",
    "ceph.aggregate_pct_used",
    "ceph.num_objects",
    "ceph.read_bytes",
    "ceph.write_bytes",
    "ceph.num_pools",
    "ceph.pgstate.active_clean",
    "ceph.read_op_per_sec",
    "ceph.write_op_per_sec",
    "ceph.num_near_full_osds",
    "ceph.num_full_osds",
    "ceph.misplaced_objects",
    "ceph.misplaced_total",
    "ceph.recovering_objects_per_sec",
    "ceph.recovering_bytes_per_sec",
    "ceph.recovering_keys_per_sec",
    # "ceph.osd.pct_used",  # Not send or ceph luminous and above
]

EXPECTED_SERVICE_TAGS = ['optional:tag1']

EXPECTED_SERVICE_CHECKS = [
    'ceph.osd_down',
    'ceph.osd_orphan',
    'ceph.osd_full',
    'ceph.osd_nearfull',
    'ceph.pool_full',
    'ceph.pool_near_full',
    'ceph.pg_availability',
    'ceph.pg_degraded',
    'ceph.pg_degraded_full',
    'ceph.pg_damaged',
    'ceph.pg_not_scrubbed',
    'ceph.pg_not_deep_scrubbed',
    'ceph.cache_pool_near_full',
    'ceph.too_few_pgs',
    'ceph.too_many_pgs',
    'ceph.object_unfound',
    'ceph.request_slow',
    'ceph.request_stuck',
]


def mock_data(filename):
    filepath = os.path.join(FIXTURE_DIR, filename)
    with open(filepath, "r") as f:
        data = f.read()
    return json.loads(data)
