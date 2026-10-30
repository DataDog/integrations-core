# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Mirrors the metrics collected by the deprecated expvar-based `go_expvar.d/agent_stats.yaml.example`, using the
# names from the Agent's `openmetrics.d/agent_stats.yaml.example`.
METRIC_MAP = {
    # Forwarder
    'transactions__dropped': 'forwarder.transactions.dropped',
    'transactions__errors': 'forwarder.transactions.errors',
    'transactions__http_errors': 'forwarder.transactions.http_errors',
    'transactions__retry_queue_size': 'forwarder.transactions.retry_queue_size',
    'transactions__success': 'forwarder.transactions.success',
    # DogStatsD
    'dogstatsd__processed': 'dogstatsd.processed',
    'dogstatsd__udp_packets': 'dogstatsd_udp.packets',
    'dogstatsd__uds_origin_detection_error': 'dogstatsd_uds.origin_detection_errors',
    'dogstatsd__uds_packets': 'dogstatsd_uds.packets',
    # Aggregator
    'aggregator__dogstatsd_contexts': 'aggregator.dogstatsd_contexts',
    'aggregator__flush': 'aggregator.flush',
    'aggregator__flush_count': 'aggregator.flush_count',
    'aggregator__flush_time': 'aggregator.flush_time',
    'aggregator__number_of_flush': 'aggregator.number_of_flush',
    'aggregator__processed': 'aggregator.processed',
    # Check scheduler
    'scheduler__checks_entered': 'scheduler.checks_entered',
    'scheduler__queue_size': 'scheduler.queues.size',
    'scheduler__queues_count': 'scheduler.queues_count',
    # Logs Agent
    'logs__bytes_sent': 'logs_agent.bytes_sent',
    'logs__decoded': 'logs_agent.logs_decoded',
    'logs__encoded_bytes_sent': 'logs_agent.encoded_bytes_sent',
    'logs__network_errors': 'logs_agent.destination_errors',
    'logs__processed': 'logs_agent.logs_processed',
    'logs__sent': 'logs_agent.logs_sent',
    'logs_client_http_destination__idle_ms': 'batch_strategy.idle_time',
    'logs_client_http_destination__in_use_ms': 'batch_strategy.in_use_time',
}
