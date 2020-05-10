# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

FOREST_STATUS_METRICS = [
    'marklogic.forests.backup-count',
    'marklogic.forests.max-stands-per-forest',
    'marklogic.forests.merge-count',
    'marklogic.forests.restore-count',
    'marklogic.forests.state-not-open',
    'marklogic.forests.total-forests',
]

FOREST_STATUS_EXTRA_METRICS = [
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
]


HOST_STATUS_METRICS = [
    # Part 1
    'marklogic.hosts.memory-process-huge-pages-size',
    'marklogic.hosts.memory-process-rss',
    'marklogic.hosts.memory-size',
    'marklogic.hosts.memory-system-free',
    'marklogic.hosts.memory-system-total',
    'marklogic.hosts.total-cpu-stat-system',
    'marklogic.hosts.total-cpu-stat-user',
    'marklogic.hosts.total-hosts',
    'marklogic.hosts.total-hosts-offline',
    # Part 2
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
    'marklogic.hosts.memory-process-swap-rate',
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
    'marklogic.servers.expanded-tree-cache-hit-rate',
    'marklogic.servers.expanded-tree-cache-miss-rate',
    'marklogic.servers.request-count',
    'marklogic.servers.request-rate',
]

TRANSACTION_STATUS_METRICS = [
    'marklogic.transactions.max-seconds',
    'marklogic.transactions.mean-seconds',
    'marklogic.transactions.median-seconds',
    'marklogic.transactions.min-seconds',
    'marklogic.transactions.ninetieth-percentile-seconds',
    'marklogic.transactions.standard-dev-seconds',
    'marklogic.transactions.total-transactions',
]


STATUS_METRICS = (FOREST_STATUS_METRICS
                  + FOREST_STATUS_EXTRA_METRICS
                  + HOST_STATUS_METRICS
                  + REQUESTS_STATUS_METRICS
                  + SERVER_STATUS_METRICS
                  + TRANSACTION_STATUS_METRICS)
