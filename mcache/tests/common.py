# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
from datadog_checks.utils.common import get_docker_hostname


HERE = os.path.dirname(os.path.abspath(__file__))

PORT = 11211
SERVICE_CHECK = 'memcache.can_connect'
HOST = get_docker_hostname()
USERNAME = 'testuser'
PASSWORD = 'testpass'

DOCKER_SOCKET_DIR = '/tmp'
DOCKER_SOCKET_PATH = '/tmp/memcached.sock'

GAUGES = [
    "memcache.total_items",
    "memcache.curr_items",
    "memcache.limit_maxbytes",
    "memcache.uptime",
    "memcache.bytes",
    "memcache.curr_connections",
    "memcache.connection_structures",
    "memcache.threads",
    "memcache.pointer_size",
    # Computed metrics
    "memcache.get_hit_percent",
    "memcache.fill_percent",
    "memcache.avg_item_size"
]

RATES = [
    "memcache.rusage_user_rate",
    "memcache.rusage_system_rate",
    "memcache.cmd_get_rate",
    "memcache.cmd_set_rate",
    "memcache.cmd_flush_rate",
    "memcache.get_hits_rate",
    "memcache.get_misses_rate",
    "memcache.delete_misses_rate",
    "memcache.delete_hits_rate",
    "memcache.evictions_rate",
    "memcache.bytes_read_rate",
    "memcache.bytes_written_rate",
    "memcache.cas_misses_rate",
    "memcache.cas_hits_rate",
    "memcache.cas_badval_rate",
    "memcache.total_connections_rate",
    "memcache.listen_disabled_num_rate"
]

# Not all rates/gauges reported by memcached test instance.
# This is the subset available with the default config/version.
ITEMS_RATES = [
    "memcache.items.evicted_rate",
    "memcache.items.evicted_nonzero_rate",
    "memcache.items.expired_unfetched_rate",
    "memcache.items.evicted_unfetched_rate",
    "memcache.items.outofmemory_rate",
    "memcache.items.tailrepairs_rate",
    "memcache.items.reclaimed_rate",
    "memcache.items.crawler_reclaimed_rate",
    "memcache.items.lrutail_reflocked_rate",
    "memcache.items.moves_to_warm_rate",
    "memcache.items.moves_to_cold_rate",
    "memcache.items.moves_within_lru_rate",
    "memcache.items.direct_reclaims_rate",
]

ITEMS_GAUGES = [
    "memcache.items.number",
    "memcache.items.number_hot",
    "memcache.items.number_warm",
    "memcache.items.number_cold",
    "memcache.items.age",
    "memcache.items.evicted_time",
]

SLABS_RATES = [
    "memcache.slabs.get_hits_rate",
    "memcache.slabs.cmd_set_rate",
    "memcache.slabs.delete_hits_rate",
    "memcache.slabs.incr_hits_rate",
    "memcache.slabs.decr_hits_rate",
    "memcache.slabs.cas_hits_rate",
    "memcache.slabs.cas_badval_rate",
    "memcache.slabs.touch_hits_rate",
    "memcache.slabs.used_chunks_rate",
]

SLABS_GAUGES = [
    "memcache.slabs.chunk_size",
    "memcache.slabs.chunks_per_page",
    "memcache.slabs.total_pages",
    "memcache.slabs.total_chunks",
    "memcache.slabs.used_chunks",
    "memcache.slabs.free_chunks",
    "memcache.slabs.free_chunks_end",
    "memcache.slabs.mem_requested",
]

SLABS_AGGREGATES = [
    "memcache.slabs.active_slabs",
    "memcache.slabs.total_malloced",
]
