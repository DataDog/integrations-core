# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# This is not actually every metric, but rather the metrics that are
# immediately available upon the start up of our environment. Some
# metrics take a while to show up and others we cannot trigger.
# Additionally, these are metrics that are present across all versions
# we support (v18-v22).
BASE_METRICS = [
    'clickhouse.background_pool.schedule.task.active',
    'clickhouse.connection.http',
    'clickhouse.connection.interserver',
    'clickhouse.connection.send.external',
    'clickhouse.connection.tcp',
    'clickhouse.dictionary.item.current',
    'clickhouse.dictionary.load',
    'clickhouse.dictionary.memory.used',
    'clickhouse.dictionary.request.cache',
    'clickhouse.file.open.read',
    'clickhouse.file.open.total',
    'clickhouse.file.open.write',
    'clickhouse.file.read.size.total',
    'clickhouse.file.read.total',
    'clickhouse.file.write.size.total',
    'clickhouse.file.write.total',
    'clickhouse.lock.context.acquisition.total',
    'clickhouse.merge.active',
    'clickhouse.merge.disk.reserved',
    'clickhouse.query.active',
    'clickhouse.query.insert.delayed',
    'clickhouse.query.memory',
    'clickhouse.query.mutation',
    'clickhouse.query.select.total',
    'clickhouse.query.total',
    'clickhouse.query.waiting',
    'clickhouse.syscall.read',
    'clickhouse.syscall.write',
    'clickhouse.table.buffer.row',
    'clickhouse.table.buffer.size',
    'clickhouse.table.distributed.connection.inserted',
    'clickhouse.table.mergetree.part.current',
    'clickhouse.table.mergetree.row.current',
    'clickhouse.table.mergetree.size',
    'clickhouse.table.replicated.active',
    'clickhouse.table.replicated.log.max',
    'clickhouse.table.replicated.log.pointer',
    'clickhouse.table.replicated.part.check',
    'clickhouse.table.replicated.part.fetch',
    'clickhouse.table.replicated.part.future',
    'clickhouse.table.replicated.part.send',
    'clickhouse.table.replicated.part.suspect',
    'clickhouse.table.replicated.queue.insert',
    'clickhouse.table.replicated.queue.merge',
    'clickhouse.table.replicated.queue.size',
    'clickhouse.table.replicated.readonly',
    'clickhouse.table.replicated.total',
    'clickhouse.table.replicated.version',
    'clickhouse.thread.lock.context.waiting',
    'clickhouse.thread.lock.rw.active.read',
    'clickhouse.thread.lock.rw.active.write',
    'clickhouse.thread.lock.rw.waiting.read',
    'clickhouse.thread.lock.rw.waiting.write',
    'clickhouse.thread.query',
    'clickhouse.zk.connection',
    'clickhouse.zk.node.ephemeral',
    'clickhouse.zk.request',
    'clickhouse.zk.watch',
]

V_18_19_METRICS = [
    'clickhouse.background_pool.processing.task.active',
    'clickhouse.background_pool.processing.memory',
    'clickhouse.background_pool.schedule.memory',
    'clickhouse.merge.memory',
    'clickhouse.replica.leader.election',
    'clickhouse.table.replicated.leader',
]

V_20_METRICS = [
    'clickhouse.background_pool.processing.task.active',
    'clickhouse.background_pool.buffer_flush_schedule.task.active',
    'clickhouse.background_pool.distributed.task.active',
    'clickhouse.background_pool.fetches.task.active',
    'clickhouse.background_pool.message_broker.task.active',
    'clickhouse.postgresql.connection',
    'clickhouse.tables_to_drop.queue.total',
    'clickhouse.query.time',
    'clickhouse.query.select.time',
    'clickhouse.selected.rows.total',
    'clickhouse.selected.bytes.total',
]

V_21_METRICS = [
    'clickhouse.background_pool.processing.task.active',
    'clickhouse.ddl.max_processed',
    'clickhouse.parts.committed',
    'clickhouse.parts.compact',
    'clickhouse.parts.delete_on_destroy',
    'clickhouse.parts.deleting',
    'clickhouse.parts.inmemory',
    'clickhouse.parts.outdated',
    'clickhouse.parts.precommitted',
    'clickhouse.parts.temporary',
]

V_22_METRICS = [
    'clickhouse.parts.pre_active',
    'clickhouse.parts.active',
]

version_mapper = {
    '18': V_18_19_METRICS,
    '19': V_18_19_METRICS,
    '20': V_20_METRICS,
    '21': V_21_METRICS,
    '22': V_22_METRICS,
}


def get_metrics(version):
    return BASE_METRICS + version_mapper.get(version.split(".")[0], [])
