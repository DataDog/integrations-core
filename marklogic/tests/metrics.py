# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

FOREST_STATUS_SUMMARY_METRICS = [
    # from /manage/v2
    'marklogic.forests.backup-count',
    'marklogic.forests.max-stands-per-forest',
    'marklogic.forests.merge-count',
    'marklogic.forests.restore-count',
    'marklogic.forests.state-not-open',
    'marklogic.forests.total-forests',
    # from /manage/v2/forests
    'marklogic.forests.backup-read-load',
    'marklogic.forests.backup-read-rate',
    'marklogic.forests.backup-write-load',
    'marklogic.forests.backup-write-rate',
    'marklogic.forests.database-replication-receive-load',
    'marklogic.forests.database-replication-receive-rate',
    'marklogic.forests.database-replication-send-load',
    'marklogic.forests.database-replication-send-rate',
    'marklogic.forests.deadlock-rate',
    'marklogic.forests.deadlock-wait-load',
    'marklogic.forests.journal-write-load',
    'marklogic.forests.journal-write-rate',
    'marklogic.forests.large-read-load',
    'marklogic.forests.large-read-rate',
    'marklogic.forests.large-write-load',
    'marklogic.forests.large-write-rate',
    'marklogic.forests.merge-read-load',
    'marklogic.forests.merge-read-rate',
    'marklogic.forests.merge-write-load',
    'marklogic.forests.merge-write-rate',
    'marklogic.forests.min-capacity',
    'marklogic.forests.query-read-load',
    'marklogic.forests.query-read-rate',
    'marklogic.forests.read-lock-hold-load',
    'marklogic.forests.read-lock-rate',
    'marklogic.forests.read-lock-wait-load',
    'marklogic.forests.restore-read-load',
    'marklogic.forests.restore-read-rate',
    'marklogic.forests.restore-write-load',
    'marklogic.forests.restore-write-rate',
    'marklogic.forests.save-write-load',
    'marklogic.forests.save-write-rate',
    'marklogic.forests.total-load',
    'marklogic.forests.total-rate',
    'marklogic.forests.write-lock-hold-load',
    'marklogic.forests.write-lock-rate',
    'marklogic.forests.write-lock-wait-load',
    # Cached
    'marklogic.forests.large-binary-cache-hit-rate',
    'marklogic.forests.large-binary-cache-miss-rate',
    'marklogic.forests.list-cache-hit-rate',
    'marklogic.forests.list-cache-miss-rate',
    'marklogic.forests.list-cache-ratio',
    'marklogic.forests.triple-cache-hit-rate',
    'marklogic.forests.triple-cache-miss-rate',
    'marklogic.forests.triple-value-cache-hit-rate',
    'marklogic.forests.triple-value-cache-miss-rate',
]

FOREST_STATUS_TREE_CACHE_METRICS = [
    'marklogic.forests.compressed-tree-cache-hit-rate',
    'marklogic.forests.compressed-tree-cache-miss-rate',
    'marklogic.forests.compressed-tree-cache-ratio',
]

HOST_STATUS_METRICS_SPECIFIC_OPTIONAL = [
    # TODO: needs preprocessing to be available
    'marklogic.hosts.memory-process-huge-pages-size',
    'marklogic.hosts.memory-process-rss',
    'marklogic.hosts.memory-system-free',
    'marklogic.hosts.memory-system-total',
    'marklogic.hosts.total-cpu-stat-system',
    'marklogic.hosts.total-cpu-stat-user',
]


HOST_STATUS_METRICS_SPECIFIC = [
    'marklogic.hosts.memory-process-swap-rate',
    'marklogic.hosts.total-hosts',
    'marklogic.hosts.total-hosts-offline',
    'marklogic.hosts.memory-size',
]

HOST_STATUS_METRICS_GENERAL = [
    'marklogic.hosts.backup-read-load',
    'marklogic.hosts.backup-read-rate',
    'marklogic.hosts.backup-write-load',
    'marklogic.hosts.backup-write-rate',
    'marklogic.hosts.deadlock-rate',
    'marklogic.hosts.deadlock-wait-load',
    'marklogic.hosts.external-binary-read-load',
    'marklogic.hosts.external-binary-read-rate',
    'marklogic.hosts.foreign-xdqp-client-receive-load',
    'marklogic.hosts.foreign-xdqp-client-receive-rate',
    'marklogic.hosts.foreign-xdqp-client-send-load',
    'marklogic.hosts.foreign-xdqp-client-send-rate',
    'marklogic.hosts.foreign-xdqp-server-receive-load',
    'marklogic.hosts.foreign-xdqp-server-receive-rate',
    'marklogic.hosts.foreign-xdqp-server-send-load',
    'marklogic.hosts.foreign-xdqp-server-send-rate',
    'marklogic.hosts.journal-write-load',
    'marklogic.hosts.journal-write-rate',
    'marklogic.hosts.large-read-load',
    'marklogic.hosts.large-read-rate',
    'marklogic.hosts.large-write-load',
    'marklogic.hosts.large-write-rate',
    'marklogic.hosts.memory-system-pagein-rate',
    'marklogic.hosts.memory-system-pageout-rate',
    'marklogic.hosts.memory-system-swapin-rate',
    'marklogic.hosts.memory-system-swapout-rate',
    'marklogic.hosts.merge-read-load',
    'marklogic.hosts.merge-read-rate',
    'marklogic.hosts.merge-write-load',
    'marklogic.hosts.merge-write-rate',
    'marklogic.hosts.query-read-load',
    'marklogic.hosts.query-read-rate',
    'marklogic.hosts.read-lock-hold-load',
    'marklogic.hosts.read-lock-rate',
    'marklogic.hosts.read-lock-wait-load',
    'marklogic.hosts.restore-read-load',
    'marklogic.hosts.restore-read-rate',
    'marklogic.hosts.restore-write-load',
    'marklogic.hosts.restore-write-rate',
    'marklogic.hosts.save-write-load',
    'marklogic.hosts.save-write-rate',
    'marklogic.hosts.total-load',
    'marklogic.hosts.total-rate',
    'marklogic.hosts.write-lock-hold-load',
    'marklogic.hosts.write-lock-rate',
    'marklogic.hosts.write-lock-wait-load',
    'marklogic.hosts.xdqp-client-receive-load',
    'marklogic.hosts.xdqp-client-receive-rate',
    'marklogic.hosts.xdqp-client-send-load',
    'marklogic.hosts.xdqp-client-send-rate',
    'marklogic.hosts.xdqp-server-receive-load',
    'marklogic.hosts.xdqp-server-receive-rate',
    'marklogic.hosts.xdqp-server-send-load',
    'marklogic.hosts.xdqp-server-send-rate',
]


REQUESTS_STATUS_METRICS = [
    # from /manage/v2
    'marklogic.requests.max-seconds',
    'marklogic.requests.mean-seconds',
    'marklogic.requests.median-seconds',
    'marklogic.requests.min-seconds',
    'marklogic.requests.ninetieth-percentile-seconds',
    'marklogic.requests.query-count',
    'marklogic.requests.standard-dev-seconds',
    'marklogic.requests.total-requests',
    'marklogic.requests.update-count',
]


SERVER_STATUS_METRICS = [
    # from /manage/v2
    'marklogic.servers.expanded-tree-cache-hit-rate',
    'marklogic.servers.expanded-tree-cache-miss-rate',
    'marklogic.servers.request-count',
    'marklogic.servers.request-rate',
]

TRANSACTION_STATUS_METRICS = [
    # from /manage/v2
    'marklogic.transactions.max-seconds',
    'marklogic.transactions.mean-seconds',
    'marklogic.transactions.median-seconds',
    'marklogic.transactions.min-seconds',
    'marklogic.transactions.ninetieth-percentile-seconds',
    'marklogic.transactions.standard-dev-seconds',
    'marklogic.transactions.total-transactions',
]


STORAGE_HOST_METRICS = [
    'marklogic.forests.storage.host.capacity',
    'marklogic.forests.storage.host.device-space',
    'marklogic.forests.storage.host.forest-reserve',
    'marklogic.forests.storage.host.forest-size',
    'marklogic.forests.storage.host.large-data-size',
    'marklogic.forests.storage.host.remaining-space',
]


STORAGE_FOREST_METRICS = [
    'marklogic.forests.storage.disk-size',
]

RESOURCE_STORAGE_FOREST_METRICS = [
    'marklogic.forests.current-foreign-master-cluster',
    'marklogic.forests.current-foreign-master-fsn',
    'marklogic.forests.current-master-fsn',
    'marklogic.forests.device-space',
    'marklogic.forests.forest-reserve',
    'marklogic.forests.journals-size',
    'marklogic.forests.large-binary-cache-hits',
    'marklogic.forests.large-binary-cache-misses',
    'marklogic.forests.large-data-size',
    'marklogic.forests.max-query-timestamp',
    'marklogic.forests.nonblocking-timestamp',
    'marklogic.forests.orphaned-binaries',
]

RESOURCE_STATUS_DATABASE_METRICS = [
    'marklogic.databases.average-forest-size',
    'marklogic.databases.backup-count',
    'marklogic.databases.backup-read-load',
    'marklogic.databases.backup-read-rate',
    'marklogic.databases.backup-write-load',
    'marklogic.databases.backup-write-rate',
    'marklogic.databases.compressed-tree-cache-hit-rate',
    'marklogic.databases.compressed-tree-cache-miss-rate',
    'marklogic.databases.data-size',
    'marklogic.databases.database-replication-receive-load',
    'marklogic.databases.database-replication-receive-rate',
    'marklogic.databases.database-replication-send-load',
    'marklogic.databases.database-replication-send-rate',
    'marklogic.databases.deadlock-rate',
    'marklogic.databases.deadlock-wait-load',
    'marklogic.databases.device-space',
    'marklogic.databases.fast-data-size',
    'marklogic.databases.forests-count',
    'marklogic.databases.in-memory-size',
    'marklogic.databases.journal-write-load',
    'marklogic.databases.journal-write-rate',
    'marklogic.databases.large-binary-cache-hit-rate',
    'marklogic.databases.large-binary-cache-miss-rate',
    'marklogic.databases.large-data-size',
    'marklogic.databases.large-read-load',
    'marklogic.databases.large-read-rate',
    'marklogic.databases.large-write-load',
    'marklogic.databases.large-write-rate',
    'marklogic.databases.largest-forest-size',
    'marklogic.databases.least-remaining-space-forest',
    'marklogic.databases.list-cache-hit-rate',
    'marklogic.databases.list-cache-miss-rate',
    'marklogic.databases.merge-count',
    'marklogic.databases.merge-read-load',
    'marklogic.databases.merge-read-rate',
    'marklogic.databases.merge-write-load',
    'marklogic.databases.merge-write-rate',
    'marklogic.databases.min-capacity',
    'marklogic.databases.query-read-load',
    'marklogic.databases.query-read-rate',
    'marklogic.databases.read-lock-hold-load',
    'marklogic.databases.read-lock-rate',
    'marklogic.databases.read-lock-wait-load',
    'marklogic.databases.reindex-count',
    'marklogic.databases.restore-count',
    'marklogic.databases.restore-read-load',
    'marklogic.databases.restore-read-rate',
    'marklogic.databases.restore-write-load',
    'marklogic.databases.restore-write-rate',
    'marklogic.databases.save-write-load',
    'marklogic.databases.save-write-rate',
    'marklogic.databases.total-load',
    'marklogic.databases.total-merge-size',
    'marklogic.databases.total-rate',
    'marklogic.databases.triple-cache-hit-rate',
    'marklogic.databases.triple-cache-miss-rate',
    'marklogic.databases.triple-value-cache-hit-rate',
    'marklogic.databases.triple-value-cache-miss-rate',
    'marklogic.databases.write-lock-hold-load',
    'marklogic.databases.write-lock-rate',
    'marklogic.databases.write-lock-wait-load',
]


HOST_STATUS_METRICS = HOST_STATUS_METRICS_GENERAL + HOST_STATUS_METRICS_SPECIFIC

GLOBAL_METRICS = (
    FOREST_STATUS_SUMMARY_METRICS
    + HOST_STATUS_METRICS
    + REQUESTS_STATUS_METRICS
    + SERVER_STATUS_METRICS
    + TRANSACTION_STATUS_METRICS
)

OPTIONAL_METRICS = HOST_STATUS_METRICS_SPECIFIC_OPTIONAL
