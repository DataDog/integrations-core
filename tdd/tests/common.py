# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 27017
PORT_ERROR = 33333

COMPOSE_FILE = os.getenv('COMPOSE_FILE')
IS_STANDALONE = COMPOSE_FILE == 'mongo-standalone.yaml'

standalone = pytest.mark.skipif(not IS_STANDALONE, reason='Test only valid for standalone mongo')

MONGODB_VERSION = os.environ['MONGO_VERSION']

ROOT = os.path.dirname(os.path.dirname(HERE))

INSTANCE_BASIC = {'hosts': ['{}:{}'.format(HOST, PORT)]}

SERVERSTATUS_METRICS = {
    "tdd.uptime",
    "tdd.asserts.msgps",
    "tdd.asserts.regularps",
    "tdd.asserts.rolloversps",
    "tdd.asserts.userps",
    "tdd.asserts.warningps",
    "tdd.backgroundflushing.average_ms",
    "tdd.backgroundflushing.flushesps",
    "tdd.backgroundflushing.last_ms",
    "tdd.backgroundflushing.total_ms",
}

TCMALLOC_METRICS = {
    "tdd.tcmalloc.generic.current_allocated_bytes",
    "tdd.tcmalloc.generic.heap_size",
    "tdd.tcmalloc.tcmalloc.aggressive_memory_decommit",
    "tdd.tcmalloc.tcmalloc.central_cache_free_bytes",
    "tdd.tcmalloc.tcmalloc.current_total_thread_cache_bytes",
    "tdd.tcmalloc.tcmalloc.max_total_thread_cache_bytes",
    "tdd.tcmalloc.tcmalloc.pageheap_free_bytes",
    "tdd.tcmalloc.tcmalloc.pageheap_unmapped_bytes",
    "tdd.tcmalloc.tcmalloc.thread_cache_free_bytes",
    "tdd.tcmalloc.tcmalloc.transfer_cache_free_bytes",
    "tdd.tcmalloc.tcmalloc.spinlock_total_delay_ns",
}

COLLSTATS_METRICS = {
    "tdd.collection.size",
    "tdd.collection.avgobjsize",
    "tdd.collection.count",
    "tdd.collection.capped",
    "tdd.collection.max",
    "tdd.collection.maxsize",
    "tdd.collection.storagesize",
    "tdd.collection.nindexes",
    "tdd.collection.indexsizes",
}

INDEX_STATS = {
    "tdd.collection.indexes.accesses.ops",
}

TOP_STATS = {
    "tdd.usage.commands.countps",
}
