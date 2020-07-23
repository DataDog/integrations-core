# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate

"""
Core metrics collected by default.
"""
BASE_METRICS = {
    "asserts.msg": RATE,
    "asserts.regular": RATE,
    "asserts.rollovers": RATE,
    "asserts.user": RATE,
    "asserts.warning": RATE,
    "backgroundFlushing.average_ms": GAUGE,
    "backgroundFlushing.flushes": RATE,
    "backgroundFlushing.last_ms": GAUGE,
    "backgroundFlushing.total_ms": GAUGE,
    "connections.available": GAUGE,
    "connections.current": GAUGE,
    "connections.totalCreated": GAUGE,
    "cursors.timedOut": GAUGE,  # < 2.6
    "cursors.totalOpen": GAUGE,  # < 2.6
    "extra_info.heap_usage_bytes": RATE,
    "extra_info.page_faults": RATE,
    "fsyncLocked": GAUGE,
    "globalLock.activeClients.readers": GAUGE,
    "globalLock.activeClients.total": GAUGE,
    "globalLock.activeClients.writers": GAUGE,
    "globalLock.currentQueue.readers": GAUGE,
    "globalLock.currentQueue.total": GAUGE,
    "globalLock.currentQueue.writers": GAUGE,
    "globalLock.lockTime": GAUGE,
    "globalLock.ratio": GAUGE,  # < 2.2
    "globalLock.totalTime": GAUGE,
    "indexCounters.accesses": RATE,
    "indexCounters.btree.accesses": RATE,  # < 2.4
    "indexCounters.btree.hits": RATE,  # < 2.4
    "indexCounters.btree.misses": RATE,  # < 2.4
    "indexCounters.btree.missRatio": GAUGE,  # < 2.4
    "indexCounters.hits": RATE,
    "indexCounters.misses": RATE,
    "indexCounters.missRatio": GAUGE,
    "indexCounters.resets": RATE,
    "mem.bits": GAUGE,
    "mem.mapped": GAUGE,
    "mem.mappedWithJournal": GAUGE,
    "mem.resident": GAUGE,
    "mem.virtual": GAUGE,
    "metrics.cursor.open.noTimeout": GAUGE,  # >= 2.6
    "metrics.cursor.open.pinned": GAUGE,  # >= 2.6
    "metrics.cursor.open.total": GAUGE,  # >= 2.6
    "metrics.cursor.timedOut": RATE,  # >= 2.6
    "metrics.document.deleted": RATE,
    "metrics.document.inserted": RATE,
    "metrics.document.returned": RATE,
    "metrics.document.updated": RATE,
    "metrics.getLastError.wtime.num": RATE,
    "metrics.getLastError.wtime.totalMillis": RATE,
    "metrics.getLastError.wtimeouts": RATE,
    "metrics.operation.fastmod": RATE,
    "metrics.operation.idhack": RATE,
    "metrics.operation.scanAndOrder": RATE,
    "metrics.operation.writeConflicts": RATE,
    "metrics.queryExecutor.scanned": RATE,
    "metrics.record.moves": RATE,
    "metrics.repl.apply.batches.num": RATE,
    "metrics.repl.apply.batches.totalMillis": RATE,
    "metrics.repl.apply.ops": RATE,
    "metrics.repl.buffer.count": GAUGE,
    "metrics.repl.buffer.maxSizeBytes": GAUGE,
    "metrics.repl.buffer.sizeBytes": GAUGE,
    "metrics.repl.network.bytes": RATE,
    "metrics.repl.network.getmores.num": RATE,
    "metrics.repl.network.getmores.totalMillis": RATE,
    "metrics.repl.network.ops": RATE,
    "metrics.repl.network.readersCreated": RATE,
    "metrics.repl.oplog.insert.num": RATE,
    "metrics.repl.oplog.insert.totalMillis": RATE,
    "metrics.repl.oplog.insertBytes": RATE,
    "metrics.repl.preload.docs.num": RATE,
    "metrics.repl.preload.docs.totalMillis": RATE,
    "metrics.repl.preload.indexes.num": RATE,
    "metrics.repl.preload.indexes.totalMillis": RATE,
    "metrics.repl.storage.freelist.search.bucketExhausted": RATE,
    "metrics.repl.storage.freelist.search.requests": RATE,
    "metrics.repl.storage.freelist.search.scanned": RATE,
    "metrics.ttl.deletedDocuments": RATE,
    "metrics.ttl.passes": RATE,
    "network.bytesIn": RATE,
    "network.bytesOut": RATE,
    "network.numRequests": RATE,
    "opcounters.command": RATE,
    "opcounters.delete": RATE,
    "opcounters.getmore": RATE,
    "opcounters.insert": RATE,
    "opcounters.query": RATE,
    "opcounters.update": RATE,
    "opcountersRepl.command": RATE,
    "opcountersRepl.delete": RATE,
    "opcountersRepl.getmore": RATE,
    "opcountersRepl.insert": RATE,
    "opcountersRepl.query": RATE,
    "opcountersRepl.update": RATE,
    "oplog.logSizeMB": GAUGE,
    "oplog.usedSizeMB": GAUGE,
    "oplog.timeDiff": GAUGE,
    "replSet.health": GAUGE,
    "replSet.replicationLag": GAUGE,
    "replSet.state": GAUGE,
    "replSet.votes": GAUGE,
    "replSet.voteFraction": GAUGE,
    "stats.avgObjSize": GAUGE,
    "stats.collections": GAUGE,
    "stats.dataSize": GAUGE,
    "stats.fileSize": GAUGE,
    "stats.indexes": GAUGE,
    "stats.indexSize": GAUGE,
    "stats.nsSizeMB": GAUGE,
    "stats.numExtents": GAUGE,
    "stats.objects": GAUGE,
    "stats.storageSize": GAUGE,
    "uptime": GAUGE,
}

"""
Journaling-related operations and performance report.

https://docs.mongodb.org/manual/reference/command/serverStatus/#serverStatus.dur
"""
DURABILITY_METRICS = {
    "dur.commits": GAUGE,
    "dur.commitsInWriteLock": GAUGE,
    "dur.compression": GAUGE,
    "dur.earlyCommits": GAUGE,
    "dur.journaledMB": GAUGE,
    "dur.timeMs.dt": GAUGE,
    "dur.timeMs.prepLogBuffer": GAUGE,
    "dur.timeMs.remapPrivateView": GAUGE,
    "dur.timeMs.writeToDataFiles": GAUGE,
    "dur.timeMs.writeToJournal": GAUGE,
    "dur.writeToDataFilesMB": GAUGE,
    # Required version > 3.0.0
    "dur.timeMs.commits": GAUGE,
    "dur.timeMs.commitsInWriteLock": GAUGE,
}

"""
ServerStatus use of database commands report.
Required version > 3.0.0.

https://docs.mongodb.org/manual/reference/command/serverStatus/#serverStatus.metrics.commands
"""
COMMANDS_METRICS = {
    # Required version >
    "metrics.commands.count.failed": RATE,
    "metrics.commands.count.total": GAUGE,
    "metrics.commands.createIndexes.failed": RATE,
    "metrics.commands.createIndexes.total": GAUGE,
    "metrics.commands.delete.failed": RATE,
    "metrics.commands.delete.total": GAUGE,
    "metrics.commands.eval.failed": RATE,
    "metrics.commands.eval.total": GAUGE,
    "metrics.commands.findAndModify.failed": RATE,
    "metrics.commands.findAndModify.total": GAUGE,
    "metrics.commands.insert.failed": RATE,
    "metrics.commands.insert.total": GAUGE,
    "metrics.commands.update.failed": RATE,
    "metrics.commands.update.total": GAUGE,
}

"""
ServerStatus locks report.
Required version > 3.0.0.

https://docs.mongodb.org/manual/reference/command/serverStatus/#server-status-locks
"""
LOCKS_METRICS = {
    "locks.Collection.acquireCount.R": RATE,
    "locks.Collection.acquireCount.r": RATE,
    "locks.Collection.acquireCount.W": RATE,
    "locks.Collection.acquireCount.w": RATE,
    "locks.Collection.acquireWaitCount.R": RATE,
    "locks.Collection.acquireWaitCount.W": RATE,
    "locks.Collection.timeAcquiringMicros.R": RATE,
    "locks.Collection.timeAcquiringMicros.W": RATE,
    "locks.Database.acquireCount.r": RATE,
    "locks.Database.acquireCount.R": RATE,
    "locks.Database.acquireCount.w": RATE,
    "locks.Database.acquireCount.W": RATE,
    "locks.Database.acquireWaitCount.r": RATE,
    "locks.Database.acquireWaitCount.R": RATE,
    "locks.Database.acquireWaitCount.w": RATE,
    "locks.Database.acquireWaitCount.W": RATE,
    "locks.Database.timeAcquiringMicros.r": RATE,
    "locks.Database.timeAcquiringMicros.R": RATE,
    "locks.Database.timeAcquiringMicros.w": RATE,
    "locks.Database.timeAcquiringMicros.W": RATE,
    "locks.Global.acquireCount.r": RATE,
    "locks.Global.acquireCount.R": RATE,
    "locks.Global.acquireCount.w": RATE,
    "locks.Global.acquireCount.W": RATE,
    "locks.Global.acquireWaitCount.r": RATE,
    "locks.Global.acquireWaitCount.R": RATE,
    "locks.Global.acquireWaitCount.w": RATE,
    "locks.Global.acquireWaitCount.W": RATE,
    "locks.Global.timeAcquiringMicros.r": RATE,
    "locks.Global.timeAcquiringMicros.R": RATE,
    "locks.Global.timeAcquiringMicros.w": RATE,
    "locks.Global.timeAcquiringMicros.W": RATE,
    "locks.Metadata.acquireCount.R": RATE,
    "locks.Metadata.acquireCount.W": RATE,
    "locks.MMAPV1Journal.acquireCount.r": RATE,
    "locks.MMAPV1Journal.acquireCount.w": RATE,
    "locks.MMAPV1Journal.acquireWaitCount.r": RATE,
    "locks.MMAPV1Journal.acquireWaitCount.w": RATE,
    "locks.MMAPV1Journal.timeAcquiringMicros.r": RATE,
    "locks.MMAPV1Journal.timeAcquiringMicros.w": RATE,
    "locks.oplog.acquireCount.R": RATE,
    "locks.oplog.acquireCount.w": RATE,
    "locks.oplog.acquireWaitCount.R": RATE,
    "locks.oplog.acquireWaitCount.w": RATE,
    "locks.oplog.timeAcquiringMicros.R": RATE,
    "locks.oplog.timeAcquiringMicros.w": RATE,
}

"""
TCMalloc memory allocator report.
"""
TCMALLOC_METRICS = {
    "tcmalloc.generic.current_allocated_bytes": GAUGE,
    "tcmalloc.generic.heap_size": GAUGE,
    "tcmalloc.tcmalloc.aggressive_memory_decommit": GAUGE,
    "tcmalloc.tcmalloc.central_cache_free_bytes": GAUGE,
    "tcmalloc.tcmalloc.current_total_thread_cache_bytes": GAUGE,
    "tcmalloc.tcmalloc.max_total_thread_cache_bytes": GAUGE,
    "tcmalloc.tcmalloc.pageheap_free_bytes": GAUGE,
    "tcmalloc.tcmalloc.pageheap_unmapped_bytes": GAUGE,
    "tcmalloc.tcmalloc.thread_cache_free_bytes": GAUGE,
    "tcmalloc.tcmalloc.transfer_cache_free_bytes": GAUGE,
    "tcmalloc.tcmalloc.spinlock_total_delay_ns": GAUGE,
}

"""
WiredTiger storage engine.
"""
WIREDTIGER_METRICS = {
    "wiredTiger.cache.bytes currently in the cache": (GAUGE, "wiredTiger.cache.bytes_currently_in_cache"),
    "wiredTiger.cache.failed eviction of pages that exceeded the in-memory maximum": (
        RATE,
        "wiredTiger.cache.failed_eviction_of_pages_exceeding_the_in-memory_maximum",
    ),
    "wiredTiger.cache.in-memory page splits": GAUGE,
    "wiredTiger.cache.maximum bytes configured": GAUGE,
    "wiredTiger.cache.maximum page size at eviction": GAUGE,
    "wiredTiger.cache.modified pages evicted": GAUGE,
    "wiredTiger.cache.pages read into cache": GAUGE,
    "wiredTiger.cache.pages written from cache": GAUGE,
    "wiredTiger.cache.pages currently held in the cache": (GAUGE, "wiredTiger.cache.pages_currently_held_in_cache"),
    "wiredTiger.cache.pages evicted because they exceeded the in-memory maximum": (
        RATE,
        "wiredTiger.cache.pages_evicted_exceeding_the_in-memory_maximum",
    ),
    "wiredTiger.cache.pages evicted by application threads": RATE,
    "wiredTiger.cache.tracked dirty bytes in the cache": (GAUGE, "wiredTiger.cache.tracked_dirty_bytes_in_cache"),
    "wiredTiger.cache.unmodified pages evicted": GAUGE,
    "wiredTiger.concurrentTransactions.read.available": GAUGE,
    "wiredTiger.concurrentTransactions.read.out": GAUGE,
    "wiredTiger.concurrentTransactions.read.totalTickets": GAUGE,
    "wiredTiger.concurrentTransactions.write.available": GAUGE,
    "wiredTiger.concurrentTransactions.write.out": GAUGE,
    "wiredTiger.concurrentTransactions.write.totalTickets": GAUGE,
}

"""
Usage statistics for each collection.

https://docs.mongodb.org/v3.0/reference/command/top/
"""
TOP_METRICS = {
    "commands.count": RATE,
    "commands.time": GAUGE,
    "getmore.count": RATE,
    "getmore.time": GAUGE,
    "insert.count": RATE,
    "insert.time": GAUGE,
    "queries.count": RATE,
    "queries.time": GAUGE,
    "readLock.count": RATE,
    "readLock.time": GAUGE,
    "remove.count": RATE,
    "remove.time": GAUGE,
    "total.count": RATE,
    "total.time": GAUGE,
    "update.count": RATE,
    "update.time": GAUGE,
    "writeLock.count": RATE,
    "writeLock.time": GAUGE,
}

COLLECTION_METRICS = {
    'collection.size': GAUGE,
    'collection.avgObjSize': GAUGE,
    'collection.count': GAUGE,
    'collection.capped': GAUGE,
    'collection.max': GAUGE,
    'collection.maxSize': GAUGE,
    'collection.storageSize': GAUGE,
    'collection.nindexes': GAUGE,
    'collection.indexSizes': GAUGE,
}

"""
Mapping for case-sensitive metric name suffixes.

https://docs.mongodb.org/manual/reference/command/serverStatus/#server-status-locks
"""
CASE_SENSITIVE_METRIC_NAME_SUFFIXES = {
    r'\.R\b': ".shared",
    r'\.r\b': ".intent_shared",
    r'\.W\b': ".exclusive",
    r'\.w\b': ".intent_exclusive",
}

"""
Metrics collected by default.
"""
DEFAULT_METRICS = {
    'base': BASE_METRICS,
    'durability': DURABILITY_METRICS,
    'locks': LOCKS_METRICS,
    'wiredtiger': WIREDTIGER_METRICS,
}

"""
Additional metrics by category.
"""
AVAILABLE_METRICS = {
    'metrics.commands': COMMANDS_METRICS,
    'tcmalloc': TCMALLOC_METRICS,
    'top': TOP_METRICS,
    'collection': COLLECTION_METRICS,
}
