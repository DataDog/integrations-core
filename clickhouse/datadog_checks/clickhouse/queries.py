# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .utils import compact_query

# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-metrics
SystemMetrics = {
    'name': 'system.metrics',
    'query': 'SELECT value, metric FROM system.metrics',
    'columns': [
        {'name': 'value', 'type': 'source'},
        {
            'name': 'metric',
            'type': 'match',
            'source': 'value',
            'items': {
                'ActiveAsyncDrainedConnections': {'name': 'drained_connections.async.active', 'type': 'gauge'},
                'ActiveSyncDrainedConnections': {'name': 'drained_connections.sync.active', 'type': 'gauge'},
                'AsyncDrainedConnections': {'name': 'drained_connections.async', 'type': 'gauge'},
                'BackgroundBufferFlushSchedulePoolTask': {
                    'name': 'background_pool.buffer_flush_schedule.task.active',
                    'type': 'gauge',
                },
                'BackgroundDistributedSchedulePoolTask': {
                    'name': 'background_pool.distributed.task.active',
                    'type': 'gauge',
                },
                'BackgroundFetchesPoolTask': {'name': 'background_pool.fetches.task.active', 'type': 'gauge'},
                'BackgroundMessageBrokerSchedulePoolTask': {
                    'name': 'background_pool.message_broker.task.active',
                    'type': 'gauge',
                },
                'BackgroundMovePoolTask': {'name': 'background_pool.move.task.active', 'type': 'gauge'},
                'BackgroundPoolTask': {'name': 'background_pool.processing.task.active', 'type': 'gauge'},
                'BackgroundSchedulePoolTask': {'name': 'background_pool.schedule.task.active', 'type': 'gauge'},
                'BrokenDistributedFilesToInsert': {'name': 'table.distributed.file.insert.broken', 'type': 'gauge'},
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
                'MMappedFileBytes': {'name': 'mmapped.file.size', 'type': 'gauge'},
                'MMappedFiles': {'name': 'mmapped.file.current', 'type': 'gauge'},
                'MaxDDLEntryID': {'name': 'ddl.max_processed', 'type': 'gauge'},
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
                'MemoryTrackingInBackgroundSchedulePool': {'name': 'background_pool.schedule.memory', 'type': 'gauge'},
                'Merge': {'name': 'merge.active', 'type': 'gauge'},
                'MySQLConnection': {'name': 'connection.mysql', 'type': 'gauge'},
                'NetworkReceive': {'name': 'network.threads.receive', 'type': 'gauge'},
                'NetworkSend': {'name': 'network.threads.send', 'type': 'gauge'},
                'OpenFileForRead': {'name': 'file.open.read', 'type': 'gauge'},
                'OpenFileForWrite': {'name': 'file.open.write', 'type': 'gauge'},
                'PartMutation': {'name': 'query.mutation', 'type': 'gauge'},
                'PartsActive': {'name': 'parts.active', 'type': 'gauge'},
                'PartsCommitted': {'name': 'parts.committed', 'type': 'gauge'},
                'PartsCompact': {'name': 'parts.compact', 'type': 'gauge'},
                'PartsDeleteOnDestroy': {'name': 'parts.delete_on_destroy', 'type': 'gauge'},
                'PartsDeleting': {'name': 'parts.deleting', 'type': 'gauge'},
                'PartsInMemory': {'name': 'parts.inmemory', 'type': 'gauge'},
                'PartsOutdated': {'name': 'parts.outdated', 'type': 'gauge'},
                'PartsPreCommitted': {'name': 'parts.precommitted', 'type': 'gauge'},
                'PartsTemporary': {'name': 'parts.temporary', 'type': 'gauge'},
                'PartsWide': {'name': 'parts.wide', 'type': 'gauge'},
                'PostgreSQLConnection': {'name': 'postgresql.connection', 'type': 'gauge'},
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
                'SyncDrainedConnections': {'name': 'drained_connections.sync', 'type': 'gauge'},
                'TCPConnection': {'name': 'connection.tcp', 'type': 'gauge'},
                'TablesToDropQueueSize': {'name': 'tables_to_drop.queue.total', 'type': 'gauge'},
                'Write': {'name': 'syscall.write', 'type': 'gauge'},
                'ZooKeeperRequest': {'name': 'zk.request', 'type': 'gauge'},
                'ZooKeeperSession': {'name': 'zk.connection', 'type': 'gauge'},
                'ZooKeeperWatch': {'name': 'zk.watch', 'type': 'gauge'},
            },
        },
    ],
}


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-events
SystemEvents = {
    'name': 'system.events',
    'query': 'SELECT value, event FROM system.events',
    'columns': [
        {'name': 'value', 'type': 'source'},
        {
            'name': 'event',
            'type': 'match',
            'source': 'value',
            'items': {
                'AIORead': {'name': 'aio.read', 'type': 'monotonic_gauge'},
                'AIOReadBytes': {'name': 'aio.read.size', 'type': 'monotonic_gauge'},
                'AIOWrite': {'name': 'aio.write', 'type': 'monotonic_gauge'},
                'AIOWriteBytes': {'name': 'aio.write.size', 'type': 'monotonic_gauge'},
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
                'CreatedLogEntryForMerge': {'name': 'log.entry.merge.created', 'type': 'monotonic_gauge'},
                'CreatedLogEntryForMutation': {'name': 'log.entry.mutation.created', 'type': 'monotonic_gauge'},
                'DNSError': {'name': 'error.dns', 'type': 'monotonic_gauge'},
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
                'DistributedConnectionFailAtAll': {
                    'name': 'distributed.connection.fail_at_all',
                    'type': 'monotonic_gauge',
                },
                'DistributedConnectionFailTry': {'name': 'distributed.connection.fail_try', 'type': 'monotonic_gauge'},
                'DistributedDelayedInserts': {'name': 'distributed.inserts.delayed', 'type': 'monotonic_gauge'},
                'DistributedDelayedInsertsMilliseconds': {
                    'name': 'distributed.delayed.inserts.time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'DistributedRejectedInserts': {'name': 'distributed.inserts.rejected', 'type': 'monotonic_gauge'},
                'DuplicatedInsertedBlocks': {
                    'name': 'table.mergetree.replicated.insert.deduplicate',
                    'type': 'monotonic_gauge',
                },
                'FailedInsertQuery': {'name': 'query.insert.failed', 'type': 'monotonic_gauge'},
                'FailedQuery': {'name': 'query.failed', 'type': 'monotonic_gauge'},
                'FailedSelectQuery': {'name': 'select.query.select.failed', 'type': 'monotonic_gauge'},
                'FileOpen': {'name': 'file.open', 'type': 'monotonic_gauge'},
                'HedgedRequestsChangeReplica': {
                    'name': 'table.replica.change.hedged_requests',
                    'type': 'monotonic_gauge',
                },
                'InsertQuery': {'name': 'query.insert', 'type': 'monotonic_gauge'},
                'InsertQueryTimeMicroseconds': {
                    'name': 'insert.query.time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'InsertedBytes': {'name': 'table.insert.size', 'type': 'monotonic_gauge'},
                'InsertedRows': {'name': 'table.insert.row', 'type': 'monotonic_gauge'},
                'LeaderElectionAcquiredLeadership': {
                    'name': 'table.mergetree.replicated.leader.elected',
                    'type': 'monotonic_gauge',
                },
                'Merge': {'name': 'merge', 'type': 'monotonic_gauge'},
                'MergeTreeDataProjectionWriterBlocks': {
                    'name': 'table.mergetree.insert.block.projection',
                    'type': 'monotonic_gauge',
                },
                'MergeTreeDataProjectionWriterBlocksAlreadySorted': {
                    'name': 'table.mergetree.insert.block.already_sorted.projection',
                    'type': 'monotonic_gauge',
                },
                'MergeTreeDataProjectionWriterCompressedBytes': {
                    'name': 'table.mergetree.insert.block.size.compressed.projection',
                    'type': 'monotonic_gauge',
                },
                'MergeTreeDataProjectionWriterRows': {
                    'name': 'table.mergetree.insert.write.row.projection',
                    'type': 'monotonic_gauge',
                },
                'MergeTreeDataProjectionWriterUncompressedBytes': {
                    'name': 'table.mergetree.insert.write.size.uncompressed.projection',
                    'type': 'monotonic_gauge',
                },
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
                'MergesTimeMilliseconds': {'name': 'merge.time', 'type': 'temporal_percent', 'scale': 'millisecond'},
                'NetworkReceiveBytes': {'name': 'network.receive.size', 'type': 'monotonic_gauge'},
                'NetworkReceiveElapsedMicroseconds': {
                    'name': 'network.receive.elapsed.time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'NetworkSendBytes': {'name': 'network.send.size', 'type': 'monotonic_gauge'},
                'NetworkSendElapsedMicroseconds': {
                    'name': 'network.send.elapsed.time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'NotCreatedLogEntryForMerge': {'name': 'log.entry.merge.not_created', 'type': 'monotonic_gauge'},
                'NotCreatedLogEntryForMutation': {
                    'name': 'log.entry.mutation.not_created',
                    'type': 'monotonic_gauge',
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
                'OSIOWaitMicroseconds': {'name': 'thread.io.wait', 'type': 'temporal_percent', 'scale': 'microsecond'},
                'OSReadBytes': {'name': 'disk.read.size', 'type': 'monotonic_gauge'},
                'OSReadChars': {'name': 'fs.read.size', 'type': 'monotonic_gauge'},
                'OSWriteBytes': {'name': 'disk.write.size', 'type': 'monotonic_gauge'},
                'OSWriteChars': {'name': 'fs.write.size', 'type': 'monotonic_gauge'},
                'PerfAlignmentFaults': {'name': 'perf.alignment.faults', 'type': 'monotonic_gauge'},
                'PerfBranchInstructions': {'name': 'perf.branch.instructions', 'type': 'monotonic_gauge'},
                'PerfBranchMisses': {'name': 'perf.branch.misses', 'type': 'monotonic_gauge'},
                'PerfBusCycles': {'name': 'perf.bus.cycles', 'type': 'monotonic_gauge'},
                'PerfCacheMisses': {'name': 'perf.cache.misses', 'type': 'monotonic_gauge'},
                'PerfCacheReferences': {'name': 'perf.cache.references', 'type': 'monotonic_gauge'},
                'PerfContextSwitches': {'name': 'perf.context.switches', 'type': 'monotonic_gauge'},
                'PerfCpuClock': {'name': 'perf.cpu.clock', 'type': 'gauge'},
                'PerfCpuCycles': {'name': 'perf.cpu.cycles', 'type': 'monotonic_gauge'},
                'PerfCpuMigrations': {'name': 'perf.cpu.migrations', 'type': 'monotonic_gauge'},
                'PerfDataTLBMisses': {'name': 'perf.data.tlb.misses', 'type': 'monotonic_gauge'},
                'PerfDataTLBReferences': {'name': 'perf.data.tlb.references', 'type': 'monotonic_gauge'},
                'PerfEmulationFaults': {'name': 'perf.emulation.faults', 'type': 'monotonic_gauge'},
                'PerfInstructionTLBMisses': {'name': 'perf.instruction.tlb.misses', 'type': 'monotonic_gauge'},
                'PerfInstructionTLBReferences': {
                    'name': 'perf.instruction.tlb.references',
                    'type': 'monotonic_gauge',
                },
                'PerfInstructions': {'name': 'perf.instructions', 'type': 'monotonic_gauge'},
                'PerfLocalMemoryMisses': {'name': 'perf.local_memory.misses', 'type': 'monotonic_gauge'},
                'PerfLocalMemoryReferences': {'name': 'perf.local_memory.references', 'type': 'monotonic_gauge'},
                'PerfMinEnabledRunningTime': {
                    'name': 'perf.min_enabled.running_time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'PerfMinEnabledTime': {
                    'name': 'perf.min_enabled.min_time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'PerfRefCpuCycles': {'name': 'perf.cpu.ref_cycles', 'type': 'monotonic_gauge'},
                'PerfStalledCyclesBackend': {'name': 'perf.stalled_cycles.backend', 'type': 'monotonic_gauge'},
                'PerfStalledCyclesFrontend': {'name': 'perf.stalled_cycles.frontend', 'type': 'monotonic_gauge'},
                'PerfTaskClock': {'name': 'perf.task.clock', 'type': 'gauge'},
                'Query': {'name': 'query', 'type': 'monotonic_gauge'},
                'QueryMaskingRulesMatch': {'name': 'query.mask.match', 'type': 'monotonic_gauge'},
                'QueryMemoryLimitExceeded': {'name': 'query.memory.limit_exceeded', 'type': 'monotonic_gauge'},
                'QueryProfilerSignalOverruns': {'name': 'query.signal.dropped', 'type': 'monotonic_gauge'},
                'QueryTimeMicroseconds': {'name': 'query.time', 'type': 'temporal_percent', 'scale': 'microsecond'},
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
                'ReplicaPartialShutdown': {'name': 'table.replica.partial.shutdown', 'type': 'monotonic_gauge'},
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
                'S3ReadBytes': {'name': 's3.read.bytes', 'type': 'monotonic_gauge'},
                'S3ReadMicroseconds': {'name': 's3.read.time', 'type': 'temporal_percent', 'scale': 'microsecond'},
                'S3ReadRequestsCount': {'name': 's3.read.requests', 'type': 'monotonic_gauge'},
                'S3ReadRequestsErrors': {'name': 's3.read.requests.errors', 'type': 'monotonic_gauge'},
                'S3ReadRequestsRedirects': {'name': 's3.read.requests.redirects', 'type': 'monotonic_gauge'},
                'S3ReadRequestsThrottling': {'name': 's3.read.requests.throttling', 'type': 'monotonic_gauge'},
                'S3WriteBytes': {'name': 's3.write.bytes', 'type': 'monotonic_gauge'},
                'S3WriteMicroseconds': {'name': 's3.write.time', 'type': 'temporal_percent', 'scale': 'microsecond'},
                'S3WriteRequestsCount': {'name': 's3.write.requests', 'type': 'monotonic_gauge'},
                'S3WriteRequestsErrors': {'name': 's3.write.requests.errors', 'type': 'monotonic_gauge'},
                'S3WriteRequestsRedirects': {'name': 's3.write.requests.redirects', 'type': 'monotonic_gauge'},
                'S3WriteRequestsThrottling': {'name': 's3.write.requests.throttling', 'type': 'monotonic_gauge'},
                'Seek': {'name': 'file.seek', 'type': 'monotonic_gauge'},
                'SelectQuery': {'name': 'query.select', 'type': 'monotonic_gauge'},
                'SelectQueryTimeMicroseconds': {
                    'name': 'query.select.time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'SelectedBytes': {'name': 'selected.bytes', 'type': 'monotonic_gauge'},
                'SelectedMarks': {'name': 'table.mergetree.mark.selected', 'type': 'monotonic_gauge'},
                'SelectedParts': {'name': 'table.mergetree.part.selected', 'type': 'monotonic_gauge'},
                'SelectedRanges': {'name': 'table.mergetree.range.selected', 'type': 'monotonic_gauge'},
                'SelectedRows': {'name': 'selected.rows', 'type': 'monotonic_gauge'},
                'SleepFunctionCalls': {'name': 'sleep_function.calls', 'type': 'monotonic_gauge'},
                'SleepFunctionMicroseconds': {
                    'name': 'sleep_function.time',
                    'type': 'temporal_percent',
                    'scale': 'microsecond',
                },
                'SlowRead': {'name': 'file.read.slow', 'type': 'monotonic_gauge'},
                'StorageBufferLayerLockReadersWaitMilliseconds': {
                    'name': 'storage.buffer_layer.read.wait',
                    'type': 'temporal_percent',
                    'scale': 'millisecond',
                },
                'StorageBufferLayerLockWritersWaitMilliseconds': {
                    'name': 'storage.buffer_layer.write.wait',
                    'type': 'temporal_percent',
                    'scale': 'millisecond',
                },
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


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-asynchronous_metrics
SystemAsynchronousMetrics = {
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


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-parts
SystemParts = {
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


# https://clickhouse.yandex/docs/en/operations/system_tables/#system_tables-replicas
SystemReplicas = {
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


# https://clickhouse.yandex/docs/en/operations/system_tables/#system-dictionaries
SystemDictionaries = {
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
