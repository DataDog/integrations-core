# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.db import Query

from .utils import compact_query

# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-metrics
SystemMetrics = Query(
    {
        'name': 'system.metrics',
        'query': 'SELECT value, metric FROM system.metrics',
        'columns': [
            {'name': 'value', 'type': 'source'},
            {
                'name': 'metric',
                'type': 'match',
                'source': 'value',
                'items': {
                    'BackgroundMovePoolTask': {'name': 'background_pool.move.task.active', 'type': 'gauge'},
                    'BackgroundPoolTask': {'name': 'background_pool.processing.task.active', 'type': 'gauge'},
                    'BackgroundSchedulePoolTask': {'name': 'background_pool.schedule.task.active', 'type': 'gauge'},
                    'CacheDictionaryUpdateQueueBatches': {'name': 'cache_dictionary.update_queue.batches', 'type': 'gauge'},
                    'CacheDictionaryUpdateQueueKeys': {'name': 'cache_dictionary.update_queue.keys', 'type': 'gauge'},
                    'ContextLockWait': {'name': 'thread.lock.context.waiting', 'type': 'gauge'},
                    'DelayedInserts': {'name': 'query.insert.delayed', 'type': 'gauge'},
                    'DictCacheRequests': {'name': 'dictionary.request.cache', 'type': 'gauge'},
                    'DiskSpaceReservedForMerge': {'name': 'merge.disk.reserved', 'type': 'gauge'},
                    'DistributedFilesToInsert': {'name': 'table.distributed.file.insert.pending', 'type': 'gauge'},
                    'DistributedSend': {'name': 'table.distributed.connection.inserted', 'type': 'gauge'},
                    'EphemeralNode': {'name': 'zk.node.ephemeral', 'type': 'gauge'},
                    'GlobalThread': {'name': 'thread.global.total', 'type': 'gauge'},
                    'GlobalThreadActive': {'name': 'thread.global.active', 'type': 'gauge'},
                    'HTTPConnection': {'name': 'connection.http', 'type': 'gauge'},
                    'InterserverConnection': {'name': 'connection.interserver', 'type': 'gauge'},
                    'LeaderElection': {'name': 'replica.leader.election', 'type': 'gauge'},
                    'LeaderReplica': {'name': 'table.replicated.leader', 'type': 'gauge'},
                    'LocalThread': {'name': 'thread.local.total', 'type': 'gauge'},
                    'LocalThreadActive': {'name': 'thread.local.active', 'type': 'gauge'},
                    'MemoryTracking': {'name': 'query.memory', 'type': 'gauge'},
                    'MemoryTrackingForMerges': {'name': 'merge.memory', 'type': 'gauge'},
                    'MemoryTrackingInBackgroundMoveProcessingPool': {
                        'name': 'background_pool.move.memory',
                        'type': 'gauge',
                    },
                    'MemoryTrackingInBackgroundProcessingPool': {
                        'name': 'background_pool.processing.memory',
                        'type': 'gauge',
                    },
                    'MemoryTrackingInBackgroundSchedulePool': {
                        'name': 'background_pool.schedule.memory',
                        'type': 'gauge',
                    },
                    'Merge': {'name': 'merge.active', 'type': 'gauge'},
                    'MySQLConnection': {'name': 'connection.mysql', 'type': 'gauge'},
                    'OpenFileForRead': {'name': 'file.open.read', 'type': 'gauge'},
                    'OpenFileForWrite': {'name': 'file.open.write', 'type': 'gauge'},
                    'PartMutation': {'name': 'query.mutation', 'type': 'gauge'},
                    'Query': {'name': 'query.active', 'type': 'gauge'},
                    'QueryPreempted': {'name': 'query.waiting', 'type': 'gauge'},
                    'QueryThread': {'name': 'thread.query', 'type': 'gauge'},
                    'RWLockActiveReaders': {'name': 'thread.lock.rw.active.read', 'type': 'gauge'},
                    'RWLockActiveWriters': {'name': 'thread.lock.rw.active.write', 'type': 'gauge'},
                    'RWLockWaitingReaders': {'name': 'thread.lock.rw.waiting.read', 'type': 'gauge'},
                    'RWLockWaitingWriters': {'name': 'thread.lock.rw.waiting.write', 'type': 'gauge'},
                    'Read': {'name': 'syscall.read', 'type': 'gauge'},
                    'ReadonlyReplica': {'name': 'table.replicated.readonly', 'type': 'gauge'},
                    'ReplicatedChecks': {'name': 'table.replicated.part.check', 'type': 'gauge'},
                    'ReplicatedFetch': {'name': 'table.replicated.part.fetch', 'type': 'gauge'},
                    'ReplicatedSend': {'name': 'table.replicated.part.send', 'type': 'gauge'},
                    'SendExternalTables': {'name': 'connection.send.external', 'type': 'gauge'},
                    'SendScalars': {'name': 'connection.send.scalar', 'type': 'gauge'},
                    'StorageBufferBytes': {'name': 'table.buffer.size', 'type': 'gauge'},
                    'StorageBufferRows': {'name': 'table.buffer.row', 'type': 'gauge'},
                    'TCPConnection': {'name': 'connection.tcp', 'type': 'gauge'},
                    'Write': {'name': 'syscall.write', 'type': 'gauge'},
                    'ZooKeeperRequest': {'name': 'zk.request', 'type': 'gauge'},
                    'ZooKeeperSession': {'name': 'zk.connection', 'type': 'gauge'},
                    'ZooKeeperWatch': {'name': 'zk.watch', 'type': 'gauge'},
                },
            },
        ],
    }
)


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-events
SystemEvents = Query(
    {
        'name': 'system.events',
        'query': 'SELECT value, event FROM system.events',
        'columns': [
            {'name': 'value', 'type': 'source'},
            {
                'name': 'event',
                'type': 'match',
                'source': 'value',
                'items': {
                    'CannotRemoveEphemeralNode': {'name': 'node.remove', 'type': 'monotonic_gauge'},
                    'CannotWriteToWriteBufferDiscard': {'name': 'buffer.write.discard', 'type': 'monotonic_gauge'},
                    'CompileAttempt': {'name': 'compilation.attempt', 'type': 'monotonic_gauge'},
                    'CompileExpressionsBytes': {'name': 'compilation.size', 'type': 'monotonic_gauge'},
                    'CompileExpressionsMicroseconds': {
                        'name': 'compilation.time',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'CompileFunction': {'name': 'compilation.llvm.attempt', 'type': 'monotonic_gauge'},
                    'CompileSuccess': {'name': 'compilation.success', 'type': 'monotonic_gauge'},
                    'CompiledFunctionExecute': {'name': 'compilation.function.execute', 'type': 'monotonic_gauge'},
                    'CompressedReadBufferBlocks': {'name': 'read.compressed.block', 'type': 'monotonic_gauge'},
                    'CompressedReadBufferBytes': {'name': 'read.compressed.raw.size', 'type': 'monotonic_gauge'},
                    'ContextLock': {'name': 'lock.context.acquisition', 'type': 'monotonic_gauge'},
                    'CreatedHTTPConnections': {'name': 'connection.http.create', 'type': 'monotonic_gauge'},
                    'DelayedInserts': {'name': 'table.mergetree.insert.delayed', 'type': 'monotonic_gauge'},
                    'DelayedInsertsMilliseconds': {
                        'name': 'table.mergetree.insert.delayed.time',
                        'type': 'temporal_percent',
                        'scale': 'millisecond',
                    },
                    'DiskReadElapsedMicroseconds': {
                        'name': 'syscall.read.wait',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'DiskWriteElapsedMicroseconds': {
                        'name': 'syscall.write.wait',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'DuplicatedInsertedBlocks': {
                        'name': 'table.mergetree.replicated.insert.deduplicate',
                        'type': 'monotonic_gauge',
                    },
                    'FileOpen': {'name': 'file.open', 'type': 'monotonic_gauge'},
                    'InsertQuery': {'name': 'query.insert', 'type': 'monotonic_gauge'},
                    'InsertedBytes': {'name': 'table.insert.size', 'type': 'monotonic_gauge'},
                    'InsertedRows': {'name': 'table.insert.row', 'type': 'monotonic_gauge'},
                    'LeaderElectionAcquiredLeadership': {
                        'name': 'table.mergetree.replicated.leader.elected',
                        'type': 'monotonic_gauge',
                    },
                    'Merge': {'name': 'merge', 'type': 'monotonic_gauge'},
                    'MergeTreeDataWriterBlocks': {'name': 'table.mergetree.insert.block', 'type': 'monotonic_gauge'},
                    'MergeTreeDataWriterBlocksAlreadySorted': {
                        'name': 'table.mergetree.insert.block.already_sorted',
                        'type': 'monotonic_gauge',
                    },
                    'MergeTreeDataWriterCompressedBytes': {
                        'name': 'table.mergetree.insert.write.size.compressed',
                        'type': 'monotonic_gauge',
                    },
                    'MergeTreeDataWriterRows': {'name': 'table.mergetree.insert.row', 'type': 'monotonic_gauge'},
                    'MergeTreeDataWriterUncompressedBytes': {
                        'name': 'table.mergetree.insert.write.size.uncompressed',
                        'type': 'monotonic_gauge',
                    },
                    'MergedRows': {'name': 'merge.row.read', 'type': 'monotonic_gauge'},
                    'MergedUncompressedBytes': {'name': 'merge.read.size.uncompressed', 'type': 'monotonic_gauge'},
                    'MergesTimeMilliseconds': {
                        'name': 'merge.time',
                        'type': 'temporal_percent',
                        'scale': 'millisecond',
                    },
                    'OSCPUVirtualTimeMicroseconds': {
                        'name': 'cpu.time',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'OSCPUWaitMicroseconds': {
                        'name': 'thread.cpu.wait',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'OSIOWaitMicroseconds': {
                        'name': 'thread.io.wait',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'OSReadBytes': {'name': 'disk.read.size', 'type': 'monotonic_gauge'},
                    'OSReadChars': {'name': 'fs.read.size', 'type': 'monotonic_gauge'},
                    'OSWriteBytes': {'name': 'disk.write.size', 'type': 'monotonic_gauge'},
                    'OSWriteChars': {'name': 'fs.write.size', 'type': 'monotonic_gauge'},
                    'Query': {'name': 'query', 'type': 'monotonic_gauge'},
                    'QueryMaskingRulesMatch': {'name': 'query.mask.match', 'type': 'monotonic_gauge'},
                    'QueryProfilerSignalOverruns': {'name': 'query.signal.dropped', 'type': 'monotonic_gauge'},
                    'ReadBackoff': {'name': 'query.read.backoff', 'type': 'monotonic_gauge'},
                    'ReadBufferFromFileDescriptorRead': {'name': 'file.read', 'type': 'monotonic_gauge'},
                    'ReadBufferFromFileDescriptorReadBytes': {'name': 'file.read.size', 'type': 'monotonic_gauge'},
                    'ReadBufferFromFileDescriptorReadFailed': {'name': 'file.read.fail', 'type': 'monotonic_gauge'},
                    'ReadCompressedBytes': {'name': 'read.compressed.size', 'type': 'monotonic_gauge'},
                    'RealTimeMicroseconds': {
                        'name': 'thread.process_time',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'RegexpCreated': {'name': 'compilation.regex', 'type': 'monotonic_gauge'},
                    'RejectedInserts': {'name': 'table.mergetree.insert.block.rejected', 'type': 'monotonic_gauge'},
                    'ReplicaYieldLeadership': {'name': 'table.replicated.leader.yield', 'type': 'monotonic_gauge'},
                    'ReplicatedDataLoss': {'name': 'table.replicated.part.loss', 'type': 'monotonic_gauge'},
                    'ReplicatedPartFailedFetches': {
                        'name': 'table.mergetree.replicated.fetch.replica.fail',
                        'type': 'monotonic_gauge',
                    },
                    'ReplicatedPartFetches': {
                        'name': 'table.mergetree.replicated.fetch.replica',
                        'type': 'monotonic_gauge',
                    },
                    'ReplicatedPartFetchesOfMerged': {
                        'name': 'table.mergetree.replicated.fetch.merged',
                        'type': 'monotonic_gauge',
                    },
                    'ReplicatedPartMerges': {'name': 'table.mergetree.replicated.merge', 'type': 'monotonic_gauge'},
                    'Seek': {'name': 'file.seek', 'type': 'monotonic_gauge'},
                    'SelectQuery': {'name': 'query.select', 'type': 'monotonic_gauge'},
                    'SelectedMarks': {'name': 'table.mergetree.mark.selected', 'type': 'monotonic_gauge'},
                    'SelectedParts': {'name': 'table.mergetree.part.selected', 'type': 'monotonic_gauge'},
                    'SelectedRanges': {'name': 'table.mergetree.range.selected', 'type': 'monotonic_gauge'},
                    'SlowRead': {'name': 'file.read.slow', 'type': 'monotonic_gauge'},
                    'SystemTimeMicroseconds': {
                        'name': 'thread.system.process_time',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'ThrottlerSleepMicroseconds': {
                        'name': 'query.sleep.time',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'UserTimeMicroseconds': {
                        'name': 'thread.user.process_time',
                        'type': 'temporal_percent',
                        'scale': 'microsecond',
                    },
                    'WriteBufferFromFileDescriptorWrite': {'name': 'file.write', 'type': 'monotonic_gauge'},
                    'WriteBufferFromFileDescriptorWriteBytes': {'name': 'file.write.size', 'type': 'monotonic_gauge'},
                    'WriteBufferFromFileDescriptorWriteFailed': {'name': 'file.write.fail', 'type': 'monotonic_gauge'},
                },
            },
        ],
    }
)


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-asynchronous_metrics
SystemAsynchronousMetrics = Query(
    {
        'name': 'system.asynchronous_metrics',
        'query': 'SELECT value, metric FROM system.asynchronous_metrics',
        'columns': [
            {'name': 'value', 'type': 'source'},
            {
                'name': 'metric',
                'type': 'match',
                'source': 'value',
                'items': {
                    'CompiledExpressionCacheCount': {'name': 'CompiledExpressionCacheCount', 'type': 'gauge'},
                    'MarkCacheBytes': {'name': 'table.mergetree.storage.mark.cache', 'type': 'gauge'},
                    'MarkCacheFiles': {'name': 'MarkCacheFiles', 'type': 'gauge'},
                    'MaxPartCountForPartition': {'name': 'part.max', 'type': 'gauge'},
                    'NumberOfDatabases': {'name': 'database.total', 'type': 'gauge'},
                    'NumberOfTables': {'name': 'table.total', 'type': 'gauge'},
                    'ReplicasMaxAbsoluteDelay': {'name': 'replica.delay.absolute', 'type': 'gauge'},
                    'ReplicasMaxInsertsInQueue': {'name': 'ReplicasMaxInsertsInQueue', 'type': 'gauge'},
                    'ReplicasMaxMergesInQueue': {'name': 'ReplicasMaxMergesInQueue', 'type': 'gauge'},
                    'ReplicasMaxQueueSize': {'name': 'ReplicasMaxQueueSize', 'type': 'gauge'},
                    'ReplicasMaxRelativeDelay': {'name': 'replica.delay.relative', 'type': 'gauge'},
                    'ReplicasSumInsertsInQueue': {'name': 'ReplicasSumInsertsInQueue', 'type': 'gauge'},
                    'ReplicasSumMergesInQueue': {'name': 'ReplicasSumMergesInQueue', 'type': 'gauge'},
                    'ReplicasSumQueueSize': {'name': 'replica.queue.size', 'type': 'gauge'},
                    'UncompressedCacheBytes': {'name': 'UncompressedCacheBytes', 'type': 'gauge'},
                    'UncompressedCacheCells': {'name': 'UncompressedCacheCells', 'type': 'gauge'},
                    'Uptime': {'name': 'uptime', 'type': 'gauge'},
                    'jemalloc.active': {'name': 'jemalloc.active', 'type': 'gauge'},
                    'jemalloc.allocated': {'name': 'jemalloc.allocated', 'type': 'gauge'},
                    'jemalloc.background_thread.num_runs': {
                        'name': 'jemalloc.background_thread.num_runs',
                        'type': 'gauge',
                    },
                    'jemalloc.background_thread.num_threads': {
                        'name': 'jemalloc.background_thread.num_threads',
                        'type': 'gauge',
                    },
                    'jemalloc.background_thread.run_interval': {
                        'name': 'jemalloc.background_thread.run_interval',
                        'type': 'gauge',
                    },
                    'jemalloc.mapped': {'name': 'jemalloc.mapped', 'type': 'gauge'},
                    'jemalloc.metadata': {'name': 'jemalloc.metadata', 'type': 'gauge'},
                    'jemalloc.metadata_thp': {'name': 'jemalloc.metadata_thp', 'type': 'gauge'},
                    'jemalloc.resident': {'name': 'jemalloc.resident', 'type': 'gauge'},
                    'jemalloc.retained': {'name': 'jemalloc.retained', 'type': 'gauge'},
                },
            },
        ],
    }
)


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-parts
SystemParts = Query(
    {
        'name': 'system.parts',
        'query': compact_query(
            """
            SELECT
              database,
              table,
              sum(bytes_on_disk) AS bytes,
              count() AS parts,
              sum(rows) AS rows
            FROM system.parts
            WHERE active = 1
            GROUP BY
              database,
              table
            """
        ),
        'columns': [
            {'name': 'database', 'type': 'tag'},
            {'name': 'table', 'type': 'tag'},
            {'name': 'table.mergetree.size', 'type': 'gauge'},
            {'name': 'table.mergetree.part.current', 'type': 'gauge'},
            {'name': 'table.mergetree.row.current', 'type': 'gauge'},
        ],
    }
)


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-replicas
SystemReplicas = Query(
    {
        'name': 'system.replicas',
        'query': compact_query(
            """
            SELECT
              database,
              table,
              is_leader,
              is_readonly,
              is_session_expired,
              future_parts,
              parts_to_check,
              columns_version,
              queue_size,
              inserts_in_queue,
              merges_in_queue,
              log_max_index,
              log_pointer,
              total_replicas,
              active_replicas
            FROM system.replicas
            """
        ),
        'columns': [
            {'name': 'database', 'type': 'tag'},
            {'name': 'table', 'type': 'tag'},
            {'name': 'is_leader', 'type': 'tag', 'boolean': True},
            {'name': 'is_readonly', 'type': 'tag', 'boolean': True},
            {'name': 'is_session_expired', 'type': 'tag', 'boolean': True},
            {'name': 'table.replicated.part.future', 'type': 'gauge'},
            {'name': 'table.replicated.part.suspect', 'type': 'gauge'},
            {'name': 'table.replicated.version', 'type': 'gauge'},
            {'name': 'table.replicated.queue.size', 'type': 'gauge'},
            {'name': 'table.replicated.queue.insert', 'type': 'gauge'},
            {'name': 'table.replicated.queue.merge', 'type': 'gauge'},
            {'name': 'table.replicated.log.max', 'type': 'gauge'},
            {'name': 'table.replicated.log.pointer', 'type': 'gauge'},
            {'name': 'table.replicated.total', 'type': 'gauge'},
            {'name': 'table.replicated.active', 'type': 'gauge'},
        ],
    }
)


# https://clickhouse.yandex/docs/en/operations/system_tables/#system-dictionaries
SystemDictionaries = Query(
    {
        'name': 'system.dictionaries',
        'query': compact_query(
            """
            SELECT
              name,
              bytes_allocated,
              element_count,
              load_factor
            FROM system.dictionaries
            """
        ),
        'columns': [
            {'name': 'dictionary', 'type': 'tag'},
            {'name': 'dictionary.memory.used', 'type': 'gauge'},
            {'name': 'dictionary.item.current', 'type': 'gauge'},
            {'name': 'dictionary.load', 'type': 'gauge'},
        ],
    }
)
