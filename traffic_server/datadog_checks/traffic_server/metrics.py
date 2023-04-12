# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from typing import Any, List, Optional, Tuple  # noqa: F401

SHORT_VERSION_METRIC_NAMES = ['server', 'proxy.node.version.manager.short']
VERSION_BUILD_NUMBER_METRIC_NAME = 'proxy.node.version.manager.build_number'
HOSTNAME_METRIC_NAMES = ['proxy.node.hostname_FQ', 'proxy.node.hostname']

SIMPLE_METRICS = {
    "proxy.process.http.origin_server_total_request_bytes": {
        "name": "process.http.origin_server_total_request_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_total_response_bytes": {
        "name": "process.http.origin_server_total_response_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.user_agent_total_bytes": {"name": "process.user_agent_total_bytes", "method": "monotonic_count"},
    "proxy.process.origin_server_total_bytes": {
        "name": "process.origin_server_total_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.cache_total_hits": {"name": "process.cache.total_hits", "method": "monotonic_count"},
    "proxy.process.cache_total_misses": {"name": "process.cache.total_misses", "method": "monotonic_count"},
    "proxy.process.cache_total_requests": {"name": "process.cache.total_requests", "method": "monotonic_count"},
    "proxy.process.cache_total_hits_bytes": {"name": "process.cache.total_hits_bytes", "method": "monotonic_count"},
    "proxy.process.cache_total_misses_bytes": {"name": "process.cache.total_misses_bytes", "method": "monotonic_count"},
    "proxy.process.cache_total_bytes": {"name": "process.cache.total_bytes", "method": "monotonic_count"},
    "proxy.process.http.user_agent_total_request_bytes": {
        "name": "process.http.user_agent_total_request_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_total_response_bytes": {
        "name": "process.http.user_agent_total_response_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.completed_requests": {"name": "process.http.completed_requests", "method": "monotonic_count"},
    "proxy.process.http.total_incoming_connections": {
        "name": "process.http.total_incoming_connections",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_client_connections": {
        "name": "process.http.total_client_connections",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_client_connections_ipv4": {
        "name": "process.http.total_client_connections_ipv4",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_client_connections_ipv6": {
        "name": "process.http.total_client_connections_ipv6",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_server_connections": {
        "name": "process.http.total_server_connections",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_parent_proxy_connections": {
        "name": "process.http.total_parent_proxy_connections",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_parent_retries": {
        "name": "process.http.total_parent_retries",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_parent_switches": {
        "name": "process.http.total_parent_switches",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_parent_retries_exhausted": {
        "name": "process.http.total_parent_retries_exhausted",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_parent_marked_down_count": {
        "name": "process.http.total_parent_marked_down_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.background_fill_total_count": {
        "name": "process.http.background_fill_total_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.errors.pre_accept_hangups": {
        "name": "process.http.transaction_counts.errors.pre_accept_hangups",
        "method": "monotonic_count",
    },
    "proxy.process.http.incoming_requests": {"name": "process.http.incoming_requests", "method": "monotonic_count"},
    "proxy.process.http.outgoing_requests": {"name": "process.http.outgoing_requests", "method": "monotonic_count"},
    "proxy.process.http.incoming_responses": {"name": "process.http.incoming_responses", "method": "monotonic_count"},
    "proxy.process.http.invalid_client_requests": {
        "name": "process.http.invalid_client_requests",
        "method": "monotonic_count",
    },
    "proxy.process.http.missing_host_hdr": {"name": "process.http.missing_host_hdr", "method": "monotonic_count"},
    "proxy.process.http.get_requests": {"name": "process.http.get_requests", "method": "monotonic_count"},
    "proxy.process.http.head_requests": {"name": "process.http.head_requests", "method": "monotonic_count"},
    "proxy.process.http.trace_requests": {"name": "process.http.trace_requests", "method": "monotonic_count"},
    "proxy.process.http.options_requests": {"name": "process.http.options_requests", "method": "monotonic_count"},
    "proxy.process.http.post_requests": {"name": "process.http.post_requests", "method": "monotonic_count"},
    "proxy.process.http.put_requests": {"name": "process.http.put_requests", "method": "monotonic_count"},
    "proxy.process.http.push_requests": {"name": "process.http.push_requests", "method": "monotonic_count"},
    "proxy.process.http.delete_requests": {"name": "process.http.delete_requests", "method": "monotonic_count"},
    "proxy.process.http.purge_requests": {"name": "process.http.purge_requests", "method": "monotonic_count"},
    "proxy.process.http.connect_requests": {"name": "process.http.connect_requests", "method": "monotonic_count"},
    "proxy.process.http.extension_method_requests": {
        "name": "process.http.extension_method_requests",
        "method": "monotonic_count",
    },
    "proxy.process.http.broken_server_connections": {
        "name": "process.http.broken_server_connections",
        "method": "monotonic_count",
    },
    "proxy.process.http.cache_lookups": {"name": "process.http.cache_lookups", "method": "monotonic_count"},
    "proxy.process.http.cache_writes": {"name": "process.http.cache_writes", "method": "monotonic_count"},
    "proxy.process.http.cache_updates": {"name": "process.http.cache_updates", "method": "monotonic_count"},
    "proxy.process.http.cache_deletes": {"name": "process.http.cache_deletes", "method": "monotonic_count"},
    "proxy.process.http.tunnels": {"name": "process.http.tunnels", "method": "monotonic_count"},
    "proxy.process.http.parent_proxy_transaction_time": {
        "name": "process.http.parent_proxy_transaction_time",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_request_header_total_size": {
        "name": "process.http.user_agent_request_header_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_response_header_total_size": {
        "name": "process.http.user_agent_response_header_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_request_document_total_size": {
        "name": "process.http.user_agent_request_document_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_response_document_total_size": {
        "name": "process.http.user_agent_response_document_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_request_header_total_size": {
        "name": "process.http.origin_server_request_header_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_response_header_total_size": {
        "name": "process.http.origin_server_response_header_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_request_document_total_size": {
        "name": "process.http.origin_server_request_document_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_response_document_total_size": {
        "name": "process.http.origin_server_response_document_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.parent_proxy_request_total_bytes": {
        "name": "process.http.parent_proxy_request_total_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.parent_proxy_response_total_bytes": {
        "name": "process.http.parent_proxy_response_total_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.pushed_response_header_total_size": {
        "name": "process.http.pushed_response_header_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.pushed_document_total_size": {
        "name": "process.http.pushed_document_total_size",
        "method": "monotonic_count",
    },
    "proxy.process.http.response_document_size_100": {
        "name": "process.http.response_document_size_100",
        "method": "monotonic_count",
    },
    "proxy.process.http.response_document_size_1K": {
        "name": "process.http.response_document_size_1K",
        "method": "monotonic_count",
    },
    "proxy.process.http.response_document_size_3K": {
        "name": "process.http.response_document_size_3K",
        "method": "monotonic_count",
    },
    "proxy.process.http.response_document_size_5K": {
        "name": "process.http.response_document_size_5K",
        "method": "monotonic_count",
    },
    "proxy.process.http.response_document_size_10K": {
        "name": "process.http.response_document_size_10K",
        "method": "monotonic_count",
    },
    "proxy.process.http.response_document_size_1M": {
        "name": "process.http.response_document_size_1M",
        "method": "monotonic_count",
    },
    "proxy.process.http.response_document_size_inf": {
        "name": "process.http.response_document_size_inf",
        "method": "monotonic_count",
    },
    "proxy.process.http.request_document_size_100": {
        "name": "process.http.request_document_size_100",
        "method": "monotonic_count",
    },
    "proxy.process.http.request_document_size_1K": {
        "name": "process.http.request_document_size_1K",
        "method": "monotonic_count",
    },
    "proxy.process.http.request_document_size_3K": {
        "name": "process.http.request_document_size_3K",
        "method": "monotonic_count",
    },
    "proxy.process.http.request_document_size_5K": {
        "name": "process.http.request_document_size_5K",
        "method": "monotonic_count",
    },
    "proxy.process.http.request_document_size_10K": {
        "name": "process.http.request_document_size_10K",
        "method": "monotonic_count",
    },
    "proxy.process.http.request_document_size_1M": {
        "name": "process.http.request_document_size_1M",
        "method": "monotonic_count",
    },
    "proxy.process.http.request_document_size_inf": {
        "name": "process.http.request_document_size_inf",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_transactions_time": {
        "name": "process.http.total_transactions_time",
        "method": "monotonic_count",
    },
    "proxy.process.http.cache_hit_fresh": {"name": "process.http.cache.hit_fresh", "method": "monotonic_count"},
    "proxy.process.http.cache_hit_mem_fresh": {"name": "process.http.cache.hit_mem_fresh", "method": "monotonic_count"},
    "proxy.process.http.cache_hit_revalidated": {
        "name": "process.http.cache.hit_revalidated",
        "method": "monotonic_count",
    },
    "proxy.process.http.cache_hit_ims": {"name": "process.http.cache.hit_ims", "method": "monotonic_count"},
    "proxy.process.http.cache_hit_stale_served": {
        "name": "process.http.cache.hit_stale_served",
        "method": "monotonic_count",
    },
    "proxy.process.http.cache_miss_cold": {"name": "process.http.cache.miss_cold", "method": "monotonic_count"},
    "proxy.process.http.cache_miss_changed": {"name": "process.http.cache.miss_changed", "method": "monotonic_count"},
    "proxy.process.http.cache_miss_client_no_cache": {
        "name": "process.http.cache.miss_client_no_cache",
        "method": "monotonic_count",
    },
    "proxy.process.http.cache_miss_client_not_cacheable": {
        "name": "process.http.cache.miss_client_not_cacheable",
        "method": "monotonic_count",
    },
    "proxy.process.http.cache_miss_ims": {"name": "process.http.cache.miss_ims", "method": "monotonic_count"},
    "proxy.process.http.cache_read_error": {"name": "process.http.cache.read_error", "method": "monotonic_count"},
    "proxy.process.http.user_agent_speed_bytes_per_sec_100": {
        "name": "process.http.user_agent_speed_bytes_per_sec_100",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_speed_bytes_per_sec_1K": {
        "name": "process.http.user_agent_speed_bytes_per_sec_1K",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_speed_bytes_per_sec_10K": {
        "name": "process.http.user_agent_speed_bytes_per_sec_10K",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_speed_bytes_per_sec_100K": {
        "name": "process.http.user_agent_speed_bytes_per_sec_100K",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_speed_bytes_per_sec_1M": {
        "name": "process.http.user_agent_speed_bytes_per_sec_1M",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_speed_bytes_per_sec_10M": {
        "name": "process.http.user_agent_speed_bytes_per_sec_10M",
        "method": "monotonic_count",
    },
    "proxy.process.http.user_agent_speed_bytes_per_sec_100M": {
        "name": "process.http.user_agent_speed_bytes_per_sec_100M",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_speed_bytes_per_sec_100": {
        "name": "process.http.origin_server_speed_bytes_per_sec_100",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_speed_bytes_per_sec_1K": {
        "name": "process.http.origin_server_speed_bytes_per_sec_1K",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_speed_bytes_per_sec_10K": {
        "name": "process.http.origin_server_speed_bytes_per_sec_10K",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_speed_bytes_per_sec_100K": {
        "name": "process.http.origin_server_speed_bytes_per_sec_100K",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_speed_bytes_per_sec_1M": {
        "name": "process.http.origin_server_speed_bytes_per_sec_1M",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_speed_bytes_per_sec_10M": {
        "name": "process.http.origin_server_speed_bytes_per_sec_10M",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_server_speed_bytes_per_sec_100M": {
        "name": "process.http.origin_server_speed_bytes_per_sec_100M",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_hit_count_stat": {"name": "process.http.tcp.hit_count", "method": "monotonic_count"},
    "proxy.process.http.tcp_miss_count_stat": {"name": "process.http.tcp.miss_count", "method": "monotonic_count"},
    "proxy.process.http.tcp_expired_miss_count_stat": {
        "name": "process.http.tcp.expired_miss_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_refresh_hit_count_stat": {
        "name": "process.http.tcp.refresh_hit_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_refresh_miss_count_stat": {
        "name": "process.http.tcp.refresh_miss_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_client_refresh_count_stat": {
        "name": "process.http.tcp.client_refresh_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_ims_hit_count_stat": {
        "name": "process.http.tcp.ims_hit_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_ims_miss_count_stat": {
        "name": "process.http.tcp.ims_miss_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_client_abort_count_stat": {
        "name": "process.http.error.client_abort_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_client_read_error_count_stat": {
        "name": "process.http.error.client_read_error_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_connect_fail_count_stat": {
        "name": "process.http.error.connect_fail_count",
        "method": "monotonic_count",
    },
    "proxy.process.http.misc_count_stat": {"name": "process.http.misc_count", "method": "monotonic_count"},
    "proxy.process.http.cache_write_errors": {"name": "process.http.cache_write_errors", "method": "monotonic_count"},
    "proxy.process.http.cache_read_errors": {"name": "process.http.cache_read_errors", "method": "monotonic_count"},
    "proxy.process.http.transaction_counts.hit_fresh": {
        "name": "process.http.transaction_counts.hit_fresh",
        "method": "gauge",
    },
    "proxy.process.http.transaction_totaltime.hit_fresh": {
        "name": "process.http.transaction_totaltime.hit_fresh",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.hit_fresh.process": {
        "name": "process.http.transaction_counts.hit_fresh.process",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.hit_fresh.process": {
        "name": "process.http.transaction_totaltime.hit_fresh.process",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.hit_revalidated": {
        "name": "process.http.transaction_counts.hit_revalidated",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.hit_revalidated": {
        "name": "process.http.transaction_totaltime.hit_revalidated",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.miss_cold": {
        "name": "process.http.transaction_counts.miss_cold",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.miss_cold": {
        "name": "process.http.transaction_totaltime.miss_cold",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.miss_not_cacheable": {
        "name": "process.http.transaction_counts.miss_not_cacheable",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.miss_not_cacheable": {
        "name": "process.http.transaction_totaltime.miss_not_cacheable",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.miss_changed": {
        "name": "process.http.transaction_counts.miss_changed",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.miss_changed": {
        "name": "process.http.transaction_totaltime.miss_changed",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.miss_client_no_cache": {
        "name": "process.http.transaction_counts.miss_client_no_cache",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.miss_client_no_cache": {
        "name": "process.http.transaction_totaltime.miss_client_no_cache",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.errors.aborts": {
        "name": "process.http.transaction_counts.errors.aborts",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.errors.aborts": {
        "name": "process.http.transaction_totaltime.errors.aborts",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.errors.possible_aborts": {
        "name": "process.http.transaction_counts.errors.possible_aborts",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.errors.possible_aborts": {
        "name": "process.http.transaction_totaltime.errors.possible_aborts",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.errors.connect_failed": {
        "name": "process.http.transaction_counts.errors.connect_failed",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.errors.connect_failed": {
        "name": "process.http.transaction_totaltime.errors.connect_failed",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.errors.other": {
        "name": "process.http.transaction_counts.errors.other",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.errors.other": {
        "name": "process.http.transaction_totaltime.errors.other",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_counts.other.unclassified": {
        "name": "process.http.transaction_counts.other.unclassified",
        "method": "monotonic_count",
    },
    "proxy.process.http.transaction_totaltime.other.unclassified": {
        "name": "process.http.transaction_totaltime.other.unclassified",
        "method": "monotonic_count",
    },
    "proxy.process.http.disallowed_post_100_continue": {
        "name": "process.http.disallowed_post_100_continue",
        "method": "monotonic_count",
    },
    "proxy.process.http.total_x_redirect_count": {
        "name": "process.http.total_x_redirect_count",
        "method": "monotonic_count",
    },
    "proxy.process.https.incoming_requests": {"name": "process.https.incoming_requests", "method": "monotonic_count"},
    "proxy.process.https.total_client_connections": {
        "name": "process.https.total_client_connections",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_connections_throttled_out": {
        "name": "process.http.origin_connections_throttled_out",
        "method": "monotonic_count",
    },
    "proxy.process.http.post_body_too_large": {"name": "process.http.post_body_too_large", "method": "monotonic_count"},
    "proxy.process.http.milestone.ua_begin": {"name": "process.http.milestone.ua_begin", "method": "monotonic_count"},
    "proxy.process.http.milestone.ua_first_read": {
        "name": "process.http.milestone.ua_first_read",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.ua_read_header_done": {
        "name": "process.http.milestone.ua_read_header_done",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.ua_begin_write": {
        "name": "process.http.milestone.ua_begin_write",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.ua_close": {"name": "process.http.milestone.ua_close", "method": "monotonic_count"},
    "proxy.process.http.milestone.server_first_connect": {
        "name": "process.http.milestone.server_first_connect",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.server_connect": {
        "name": "process.http.milestone.server_connect",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.server_connect_end": {
        "name": "process.http.milestone.server_connect_end",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.server_begin_write": {
        "name": "process.http.milestone.server_begin_write",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.server_first_read": {
        "name": "process.http.milestone.server_first_read",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.server_read_header_done": {
        "name": "process.http.milestone.server_read_header_done",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.server_close": {
        "name": "process.http.milestone.server_close",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.cache_open_read_begin": {
        "name": "process.http.milestone.cache_open_read_begin",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.cache_open_read_end": {
        "name": "process.http.milestone.cache_open_read_end",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.cache_open_write_begin": {
        "name": "process.http.milestone.cache_open_write_begin",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.cache_open_write_end": {
        "name": "process.http.milestone.cache_open_write_end",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.dns_lookup_begin": {
        "name": "process.http.milestone.dns_lookup_begin",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.dns_lookup_end": {
        "name": "process.http.milestone.dns_lookup_end",
        "method": "monotonic_count",
    },
    "proxy.process.http.milestone.sm_start": {"name": "process.http.milestone.sm_start", "method": "monotonic_count"},
    "proxy.process.http.milestone.sm_finish": {"name": "process.http.milestone.sm_finish", "method": "monotonic_count"},
    "proxy.process.http.dead_server.no_requests": {
        "name": "process.http.dead_server.no_requests",
        "method": "monotonic_count",
    },
    "proxy.process.net.calls_to_read": {"name": "process.net.calls_to_read", "method": "monotonic_count"},
    "proxy.process.net.calls_to_read_nodata": {"name": "process.net.calls_to_read_nodata", "method": "monotonic_count"},
    "proxy.process.net.calls_to_readfromnet": {"name": "process.net.calls_to_readfromnet", "method": "monotonic_count"},
    "proxy.process.net.calls_to_readfromnet_afterpoll": {
        "name": "process.net.calls_to_readfromnet_afterpoll",
        "method": "monotonic_count",
    },
    "proxy.process.net.calls_to_write": {"name": "process.net.calls_to_write", "method": "monotonic_count"},
    "proxy.process.net.calls_to_write_nodata": {
        "name": "process.net.calls_to_write_nodata",
        "method": "monotonic_count",
    },
    "proxy.process.net.calls_to_writetonet": {"name": "process.net.calls_to_writetonet", "method": "monotonic_count"},
    "proxy.process.net.calls_to_writetonet_afterpoll": {
        "name": "process.net.calls_to_writetonet_afterpoll",
        "method": "monotonic_count",
    },
    "proxy.process.net.net_handler_run": {"name": "process.net.net_handler_run", "method": "monotonic_count"},
    "proxy.process.net.read_bytes": {"name": "process.net.read_bytes", "method": "monotonic_count"},
    "proxy.process.net.write_bytes": {"name": "process.net.write_bytes", "method": "monotonic_count"},
    "proxy.process.net.inactivity_cop_lock_acquire_failure": {
        "name": "process.net.inactivity_cop_lock_acquire_failure",
        "method": "monotonic_count",
    },
    "proxy.process.net.fastopen_out.attempts": {
        "name": "process.net.fastopen_out.attempts",
        "method": "monotonic_count",
    },
    "proxy.process.net.fastopen_out.successes": {
        "name": "process.net.fastopen_out.successes",
        "method": "monotonic_count",
    },
    "proxy.process.socks.connections_successful": {
        "name": "process.socks.connections_successful",
        "method": "monotonic_count",
    },
    "proxy.process.socks.connections_unsuccessful": {
        "name": "process.socks.connections_unsuccessful",
        "method": "monotonic_count",
    },
    "proxy.process.net.connections_throttled_in": {
        "name": "process.net.connections_throttled_in",
        "method": "monotonic_count",
    },
    "proxy.process.net.connections_throttled_out": {
        "name": "process.net.connections_throttled_out",
        "method": "monotonic_count",
    },
    "proxy.process.net.max.requests_throttled_in": {
        "name": "process.net.max.requests_throttled_in",
        "method": "monotonic_count",
    },
    "proxy.process.hostdb.total_lookups": {"name": "process.hostdb.total_lookups", "method": "monotonic_count"},
    "proxy.process.hostdb.total_hits": {"name": "process.hostdb.total_hits", "method": "monotonic_count"},
    "proxy.process.hostdb.re_dns_on_reload": {"name": "process.hostdb.re_dns_on_reload", "method": "monotonic_count"},
    "proxy.process.dns.total_dns_lookups": {"name": "process.dns.total_dns_lookups", "method": "monotonic_count"},
    "proxy.process.dns.lookup_successes": {"name": "process.dns.lookup_successes", "method": "monotonic_count"},
    "proxy.process.dns.lookup_failures": {"name": "process.dns.lookup_failures", "method": "monotonic_count"},
    "proxy.process.dns.retries": {"name": "process.dns.retries", "method": "monotonic_count"},
    "proxy.process.dns.max_retries_exceeded": {"name": "process.dns.max_retries_exceeded", "method": "monotonic_count"},
    "proxy.process.http2.total_client_streams": {
        "name": "process.http2.total_client_streams",
        "method": "monotonic_count",
    },
    "proxy.process.http2.total_transactions_time": {
        "name": "process.http2.total_transactions_time",
        "method": "monotonic_count",
    },
    "proxy.process.http2.total_client_connections": {
        "name": "process.http2.total_client_connections",
        "method": "monotonic_count",
    },
    "proxy.process.http2.connection_errors": {"name": "process.http2.connection_errors", "method": "monotonic_count"},
    "proxy.process.http2.stream_errors": {"name": "process.http2.stream_errors", "method": "monotonic_count"},
    "proxy.process.http2.session_die_default": {
        "name": "process.http2.session_die_default",
        "method": "monotonic_count",
    },
    "proxy.process.http2.session_die_other": {"name": "process.http2.session_die_other", "method": "monotonic_count"},
    "proxy.process.http2.session_die_eos": {"name": "process.http2.session_die_eos", "method": "monotonic_count"},
    "proxy.process.http2.session_die_active": {"name": "process.http2.session_die_active", "method": "monotonic_count"},
    "proxy.process.http2.session_die_inactive": {
        "name": "process.http2.session_die_inactive",
        "method": "monotonic_count",
    },
    "proxy.process.http2.session_die_error": {"name": "process.http2.session_die_error", "method": "monotonic_count"},
    "proxy.process.http2.session_die_high_error_rate": {
        "name": "process.http2.session_die_high_error_rate",
        "method": "monotonic_count",
    },
    "proxy.process.http2.max_settings_per_frame_exceeded": {
        "name": "process.http2.max_settings_per_frame_exceeded",
        "method": "monotonic_count",
    },
    "proxy.process.http2.max_settings_per_minute_exceeded": {
        "name": "process.http2.max_settings_per_minute_exceeded",
        "method": "monotonic_count",
    },
    "proxy.process.http2.max_settings_frames_per_minute_exceeded": {
        "name": "process.http2.max_settings_frames_per_minute_exceeded",
        "method": "monotonic_count",
    },
    "proxy.process.http2.max_ping_frames_per_minute_exceeded": {
        "name": "process.http2.max_ping_frames_per_minute_exceeded",
        "method": "monotonic_count",
    },
    "proxy.process.http2.max_priority_frames_per_minute_exceeded": {
        "name": "process.http2.max_priority_frames_per_minute_exceeded",
        "method": "monotonic_count",
    },
    "proxy.process.http2.insufficient_avg_window_update": {
        "name": "process.http2.insufficient_avg_window_update",
        "method": "monotonic_count",
    },
    "proxy.process.log.event_log_error_ok": {"name": "process.log.event_log_error_ok", "method": "monotonic_count"},
    "proxy.process.log.event_log_error_skip": {"name": "process.log.event_log_error_skip", "method": "monotonic_count"},
    "proxy.process.log.event_log_error_aggr": {"name": "process.log.event_log_error_aggr", "method": "monotonic_count"},
    "proxy.process.log.event_log_error_full": {"name": "process.log.event_log_error_full", "method": "monotonic_count"},
    "proxy.process.log.event_log_error_fail": {"name": "process.log.event_log_error_fail", "method": "monotonic_count"},
    "proxy.process.log.event_log_access_ok": {"name": "process.log.event_log_access_ok", "method": "monotonic_count"},
    "proxy.process.log.event_log_access_skip": {
        "name": "process.log.event_log_access_skip",
        "method": "monotonic_count",
    },
    "proxy.process.log.event_log_access_aggr": {
        "name": "process.log.event_log_access_aggr",
        "method": "monotonic_count",
    },
    "proxy.process.log.event_log_access_full": {
        "name": "process.log.event_log_access_full",
        "method": "monotonic_count",
    },
    "proxy.process.log.event_log_access_fail": {
        "name": "process.log.event_log_access_fail",
        "method": "monotonic_count",
    },
    "proxy.process.log.num_sent_to_network": {"name": "process.log.num_sent_to_network", "method": "monotonic_count"},
    "proxy.process.log.num_lost_before_sent_to_network": {
        "name": "process.log.num_lost_before_sent_to_network",
        "method": "monotonic_count",
    },
    "proxy.process.log.num_received_from_network": {
        "name": "process.log.num_received_from_network",
        "method": "monotonic_count",
    },
    "proxy.process.log.num_flush_to_disk": {"name": "process.log.num_flush_to_disk", "method": "monotonic_count"},
    "proxy.process.log.num_lost_before_flush_to_disk": {
        "name": "process.log.num_lost_before_flush_to_disk",
        "method": "monotonic_count",
    },
    "proxy.process.log.bytes_lost_before_preproc": {
        "name": "process.log.bytes_lost_before_preproc",
        "method": "monotonic_count",
    },
    "proxy.process.log.bytes_sent_to_network": {
        "name": "process.log.bytes_sent_to_network",
        "method": "monotonic_count",
    },
    "proxy.process.log.bytes_lost_before_sent_to_network": {
        "name": "process.log.bytes_lost_before_sent_to_network",
        "method": "monotonic_count",
    },
    "proxy.process.log.bytes_received_from_network": {
        "name": "process.log.bytes_received_from_network",
        "method": "monotonic_count",
    },
    "proxy.process.log.bytes_flush_to_disk": {"name": "process.log.bytes_flush_to_disk", "method": "monotonic_count"},
    "proxy.process.log.bytes_lost_before_flush_to_disk": {
        "name": "process.log.bytes_lost_before_flush_to_disk",
        "method": "monotonic_count",
    },
    "proxy.process.log.bytes_written_to_disk": {
        "name": "process.log.bytes_written_to_disk",
        "method": "monotonic_count",
    },
    "proxy.process.log.bytes_lost_before_written_to_disk": {
        "name": "process.log.bytes_lost_before_written_to_disk",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_other_errors": {
        "name": "process.ssl.user_agent_other_errors",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_expired_cert": {
        "name": "process.ssl.user_agent_expired_cert",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_revoked_cert": {
        "name": "process.ssl.user_agent_revoked_cert",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_unknown_cert": {
        "name": "process.ssl.user_agent_unknown_cert",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_cert_verify_failed": {
        "name": "process.ssl.user_agent_cert_verify_failed",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_bad_cert": {"name": "process.ssl.user_agent_bad_cert", "method": "monotonic_count"},
    "proxy.process.ssl.user_agent_decryption_failed": {
        "name": "process.ssl.user_agent_decryption_failed",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_wrong_version": {
        "name": "process.ssl.user_agent_wrong_version",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_unknown_ca": {
        "name": "process.ssl.user_agent_unknown_ca",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_other_errors": {
        "name": "process.ssl.origin_server_other_errors",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_expired_cert": {
        "name": "process.ssl.origin_server_expired_cert",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_revoked_cert": {
        "name": "process.ssl.origin_server_revoked_cert",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_unknown_cert": {
        "name": "process.ssl.origin_server_unknown_cert",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_cert_verify_failed": {
        "name": "process.ssl.origin_server_cert_verify_failed",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_bad_cert": {
        "name": "process.ssl.origin_server_bad_cert",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_decryption_failed": {
        "name": "process.ssl.origin_server_decryption_failed",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_wrong_version": {
        "name": "process.ssl.origin_server_wrong_version",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.origin_server_unknown_ca": {
        "name": "process.ssl.origin_server_unknown_ca",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_handshake_time": {"name": "process.ssl.total_handshake_time", "method": "monotonic_count"},
    "proxy.process.ssl.total_attempts_handshake_count_in": {
        "name": "process.ssl.total_attempts_handshake_count_in",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_success_handshake_count_in": {
        "name": "process.ssl.total_success_handshake_count_in",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_attempts_handshake_count_out": {
        "name": "process.ssl.total_attempts_handshake_count_out",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_success_handshake_count_out": {
        "name": "process.ssl.total_success_handshake_count_out",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_tickets_created": {
        "name": "process.ssl.total_tickets_created",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_tickets_verified": {
        "name": "process.ssl.total_tickets_verified",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_tickets_not_found": {
        "name": "process.ssl.total_tickets_not_found",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_tickets_renewed": {
        "name": "process.ssl.total_tickets_renewed",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_tickets_verified_old_key": {
        "name": "process.ssl.total_tickets_verified_old_key",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.total_ticket_keys_renewed": {
        "name": "process.ssl.total_ticket_keys_renewed",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_session_cache_hit": {
        "name": "process.ssl.ssl_session_cache_hit",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_session_cache_new_session": {
        "name": "process.ssl.ssl_session_cache_new_session",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_session_cache_miss": {
        "name": "process.ssl.ssl_session_cache_miss",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_session_cache_eviction": {
        "name": "process.ssl.ssl_session_cache_eviction",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_session_cache_lock_contention": {
        "name": "process.ssl.ssl_session_cache_lock_contention",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.default_record_size_count": {
        "name": "process.ssl.default_record_size_count",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.max_record_size_count": {
        "name": "process.ssl.max_record_size_count",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.redo_record_size_count": {
        "name": "process.ssl.redo_record_size_count",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_error_syscall": {"name": "process.ssl.ssl_error_syscall", "method": "monotonic_count"},
    "proxy.process.ssl.ssl_error_ssl": {"name": "process.ssl.ssl_error_ssl", "method": "monotonic_count"},
    "proxy.process.ssl.ssl_error_async": {"name": "process.ssl.ssl_error_async", "method": "monotonic_count"},
    "proxy.process.ssl.ssl_sni_name_set_failure": {
        "name": "process.ssl.ssl_sni_name_set_failure",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_ocsp_revoked_cert_stat": {
        "name": "process.ssl.ssl_ocsp_revoked_cert_stat",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_ocsp_unknown_cert_stat": {
        "name": "process.ssl.ssl_ocsp_unknown_cert_stat",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.ssl_total_sslv3": {"name": "process.ssl.ssl_total_sslv3", "method": "monotonic_count"},
    "proxy.process.ssl.ssl_total_tlsv1": {"name": "process.ssl.ssl_total_tlsv1", "method": "monotonic_count"},
    "proxy.process.ssl.ssl_total_tlsv11": {"name": "process.ssl.ssl_total_tlsv11", "method": "monotonic_count"},
    "proxy.process.ssl.ssl_total_tlsv12": {"name": "process.ssl.ssl_total_tlsv12", "method": "monotonic_count"},
    "proxy.process.ssl.ssl_total_tlsv13": {"name": "process.ssl.ssl_total_tlsv13", "method": "monotonic_count"},
    "proxy.process.http.origin_shutdown.pool_lock_contention": {
        "name": "process.http.origin_shutdown.pool_lock_contention",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.migration_failure": {
        "name": "process.http.origin_shutdown.migration_failure",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_server": {
        "name": "process.http.origin_shutdown.tunnel_server",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_server_no_keep_alive": {
        "name": "process.http.origin_shutdown.tunnel_server_no_keep_alive",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_server_eos": {
        "name": "process.http.origin_shutdown.tunnel_server_eos",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_server_plugin_tunnel": {
        "name": "process.http.origin_shutdown.tunnel_server_plugin_tunnel",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_server_detach": {
        "name": "process.http.origin_shutdown.tunnel_server_detach",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_client": {
        "name": "process.http.origin_shutdown.tunnel_client",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_transform_read": {
        "name": "process.http.origin_shutdown.tunnel_transform_read",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.release_no_sharing": {
        "name": "process.http.origin_shutdown.release_no_sharing",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.release_no_server": {
        "name": "process.http.origin_shutdown.release_no_server",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.release_no_keep_alive": {
        "name": "process.http.origin_shutdown.release_no_keep_alive",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.release_invalid_response": {
        "name": "process.http.origin_shutdown.release_invalid_response",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.release_invalid_request": {
        "name": "process.http.origin_shutdown.release_invalid_request",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.release_modified": {
        "name": "process.http.origin_shutdown.release_modified",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.release_misc": {
        "name": "process.http.origin_shutdown.release_misc",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.cleanup_entry": {
        "name": "process.http.origin_shutdown.cleanup_entry",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin_shutdown.tunnel_abort": {
        "name": "process.http.origin_shutdown.tunnel_abort",
        "method": "monotonic_count",
    },
    "proxy.process.http.origin.connect.adjust_thread": {
        "name": "process.http.origin.connect.adjust_thread",
        "method": "monotonic_count",
    },
    "proxy.process.http.cache.open_write.adjust_thread": {
        "name": "process.http.cache.open_write.adjust_thread",
        "method": "monotonic_count",
    },
    "proxy.process.http.1xx_responses": {
        "name": "process.http.1xx_responses",
        "method": "monotonic_count",
    },
    "proxy.process.http.2xx_responses": {
        "name": "process.http.2xx_responses",
        "method": "monotonic_count",
    },
    "proxy.process.http.3xx_responses": {
        "name": "process.http.3xx_responses",
        "method": "monotonic_count",
    },
    "proxy.process.http.4xx_responses": {
        "name": "process.http.4xx_responses",
        "method": "monotonic_count",
    },
    "proxy.process.http.5xx_responses": {
        "name": "process.http.5xx_responses",
        "method": "monotonic_count",
    },
    "proxy.process.net.default_inactivity_timeout_applied": {
        "name": "process.net.default_inactivity_timeout_applied",
        "method": "monotonic_count",
    },
    "proxy.process.net.default_inactivity_timeout_count": {
        "name": "process.net.default_inactivity_timeout_count",
        "method": "monotonic_count",
    },
    "proxy.process.net.dynamic_keep_alive_timeout_in_count": {
        "name": "process.net.dynamic_keep_alive_timeout_in_count",
        "method": "monotonic_count",
    },
    "proxy.process.net.dynamic_keep_alive_timeout_in_total": {
        "name": "process.net.dynamic_keep_alive_timeout_in_total",
        "method": "monotonic_count",
    },
    "proxy.process.tcp.total_accepts": {"name": "process.tcp.total_accepts", "method": "monotonic_count"},
    "proxy.process.cache.bytes_used": {"name": "process.cache.bytes_used", "method": "gauge"},
    "proxy.process.cache.bytes_total": {"name": "process.cache.bytes_total", "method": "gauge"},
    "proxy.process.cache.ram_cache.total_bytes": {
        "name": "process.cache.ram_cache.total_bytes",
        "method": "gauge",
    },
    "proxy.process.cache.ram_cache.bytes_used": {
        "name": "process.cache.ram_cache.bytes_used",
        "method": "gauge",
    },
    "proxy.process.cache.ram_cache.hits": {
        "name": "process.cache.ram_cache.hits",
        "method": "gauge",
    },
    "proxy.process.cache.ram_cache.misses": {
        "name": "process.cache.ram_cache.misses",
        "method": "gauge",
    },
    "proxy.process.cache.pread_count": {"name": "process.cache.pread_count", "method": "monotonic_count"},
    "proxy.process.cache.lookup.active": {
        "name": "process.cache.lookup.active",
        "method": "gauge",
    },
    "proxy.process.cache.lookup.success": {
        "name": "process.cache.lookup.success",
        "method": "monotonic_count",
    },
    "proxy.process.cache.lookup.failure": {
        "name": "process.cache.lookup.failure",
        "method": "monotonic_count",
    },
    "proxy.process.cache.read.active": {"name": "process.cache.read.active", "method": "gauge"},
    "proxy.process.cache.read.success": {"name": "process.cache.read.success", "method": "monotonic_count"},
    "proxy.process.cache.read.failure": {"name": "process.cache.read.failure", "method": "monotonic_count"},
    "proxy.process.cache.write.active": {"name": "process.cache.write.active", "method": "gauge"},
    "proxy.process.cache.write.success": {
        "name": "process.cache.write.success",
        "method": "monotonic_count",
    },
    "proxy.process.cache.write.failure": {
        "name": "process.cache.write.failure",
        "method": "monotonic_count",
    },
    "proxy.process.cache.write.backlog.failure": {
        "name": "process.cache.write.backlog.failure",
        "method": "monotonic_count",
    },
    "proxy.process.cache.update.active": {
        "name": "process.cache.update.active",
        "method": "gauge",
    },
    "proxy.process.cache.update.success": {
        "name": "process.cache.update.success",
        "method": "monotonic_count",
    },
    "proxy.process.cache.update.failure": {
        "name": "process.cache.update.failure",
        "method": "monotonic_count",
    },
    "proxy.process.cache.remove.active": {
        "name": "process.cache.remove.active",
        "method": "gauge",
    },
    "proxy.process.cache.remove.success": {
        "name": "process.cache.remove.success",
        "method": "monotonic_count",
    },
    "proxy.process.cache.remove.failure": {
        "name": "process.cache.remove.failure",
        "method": "monotonic_count",
    },
    "proxy.process.cache.evacuate.active": {
        "name": "process.cache.evacuate.active",
        "method": "gauge",
    },
    "proxy.process.cache.evacuate.success": {
        "name": "process.cache.evacuate.success",
        "method": "monotonic_count",
    },
    "proxy.process.cache.evacuate.failure": {
        "name": "process.cache.evacuate.failure",
        "method": "monotonic_count",
    },
    "proxy.process.cache.scan.active": {"name": "process.cache.scan.active", "method": "gauge"},
    "proxy.process.cache.scan.success": {"name": "process.cache.scan.success", "method": "monotonic_count"},
    "proxy.process.cache.scan.failure": {"name": "process.cache.scan.failure", "method": "monotonic_count"},
    "proxy.process.hostdb.cache.total_inserts": {
        "name": "process.hostdb.cache.total_inserts",
        "method": "monotonic_count",
    },
    "proxy.process.hostdb.cache.total_failed_inserts": {
        "name": "process.hostdb.cache.total_failed_inserts",
        "method": "monotonic_count",
    },
    "proxy.process.hostdb.cache.total_lookups": {
        "name": "process.hostdb.cache.total_lookups",
        "method": "monotonic_count",
    },
    "proxy.process.hostdb.cache.total_hits": {
        "name": "process.hostdb.cache.total_hits",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_sessions": {
        "name": "process.ssl.user_agent_sessions",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_session_hit": {
        "name": "process.ssl.user_agent_session_hit",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_session_miss": {
        "name": "process.ssl.user_agent_session_miss",
        "method": "monotonic_count",
    },
    "proxy.process.ssl.user_agent_session_timeout": {
        "name": "process.ssl.user_agent_session_timeout",
        "method": "monotonic_count",
    },
    "proxy.node.restarts.proxy.restart_count": {
        "name": "node.restarts.proxy.restart_count",
        "method": "gauge",
    },
    "proxy.node.restarts.manager.start_time": {
        "name": "node.restarts.manager.start_time",
        "method": "gauge",
    },
    "proxy.node.restarts.proxy.start_time": {"name": "node.restarts.proxy.start_time", "method": "gauge"},
    "proxy.node.restarts.proxy.cache_ready_time": {
        "name": "node.restarts.proxy.cache_ready_time",
        "method": "gauge",
    },
    "proxy.node.restarts.proxy.stop_time": {"name": "node.restarts.proxy.stop_time", "method": "gauge"},
    "proxy.process.current_server_connections": {
        "name": "process.current_server_connections",
        "method": "gauge",
    },
    "proxy.node.proxy_running": {"name": "node.proxy_running", "method": "gauge"},
    "proxy.process.http.avg_transactions_per_client_connection": {
        "name": "process.http.avg_transactions_per_client_connection",
        "method": "gauge",
    },
    "proxy.process.http.avg_transactions_per_server_connection": {
        "name": "process.http.avg_transactions_per_server_connection",
        "method": "gauge",
    },
    "proxy.process.http.tcp_hit_user_agent_bytes_stat": {
        "name": "process.http.tcp.hit_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_hit_origin_server_bytes_stat": {
        "name": "process.http.tcp.hit_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_miss_user_agent_bytes_stat": {
        "name": "process.http.tcp.miss_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_miss_origin_server_bytes_stat": {
        "name": "process.http.tcp.miss_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_expired_miss_user_agent_bytes_stat": {
        "name": "process.http.tcp.expired_miss_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_expired_miss_origin_server_bytes_stat": {
        "name": "process.http.tcp.expired_miss_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_refresh_hit_user_agent_bytes_stat": {
        "name": "process.http.tcp.refresh_hit_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_refresh_hit_origin_server_bytes_stat": {
        "name": "process.http.tcp.refresh_hit_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_refresh_miss_user_agent_bytes_stat": {
        "name": "process.http.tcp.refresh_miss_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_refresh_miss_origin_server_bytes_stat": {
        "name": "process.http.tcp.refresh_miss_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_client_refresh_user_agent_bytes_stat": {
        "name": "process.http.tcp.client_refresh_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_client_refresh_origin_server_bytes_stat": {
        "name": "process.http.tcp.client_refresh_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_ims_hit_user_agent_bytes_stat": {
        "name": "process.http.tcp.ims_hit_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_ims_hit_origin_server_bytes_stat": {
        "name": "process.http.tcp.ims_hit_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_ims_miss_user_agent_bytes_stat": {
        "name": "process.http.tcp.ims_miss_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.tcp_ims_miss_origin_server_bytes_stat": {
        "name": "process.http.tcp.ims_miss_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_client_abort_user_agent_bytes_stat": {
        "name": "process.http.error.client_abort_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_client_abort_origin_server_bytes_stat": {
        "name": "process.http.error.client_abort_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_client_read_error_user_agent_bytes_stat": {
        "name": "process.http.error.client_read_error_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_client_read_error_origin_server_bytes_stat": {
        "name": "process.http.error.client_read_error_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_connect_fail_user_agent_bytes_stat": {
        "name": "process.http.error.connect_fail_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.err_connect_fail_origin_server_bytes_stat": {
        "name": "process.http.error.connect_fail_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.misc_user_agent_bytes_stat": {
        "name": "process.http.misc_user_agent_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.http_misc_origin_server_bytes_stat": {
        "name": "process.http.http_misc_origin_server_bytes",
        "method": "monotonic_count",
    },
    "proxy.process.http.background_fill_bytes_aborted_stat": {
        "name": "process.http.background_fill_bytes_aborted",
        "method": "monotonic_count",
    },
    "proxy.process.http.background_fill_bytes_completed_stat": {
        "name": "process.http.background_fill_bytes_completed",
        "method": "monotonic_count",
    },
    "proxy.process.cache.read_per_sec": {"name": "process.cache.read_per_sec", "method": "gauge"},
    "proxy.process.cache.write_per_sec": {"name": "process.cache.write_per_sec", "method": "gauge"},
    "proxy.process.cache.KB_read_per_sec": {"name": "process.cache.KB_read_per_sec", "method": "gauge"},
    "proxy.process.cache.KB_write_per_sec": {"name": "process.cache.KB_write_per_sec", "method": "gauge"},
    "proxy.process.hostdb.ttl": {"name": "process.hostdb.ttl", "method": "gauge"},
    "proxy.process.hostdb.ttl_expires": {"name": "process.hostdb.ttl_expires", "method": "gauge"},
    "proxy.process.hostdb.insert_duplicate_to_pending_dns": {
        "name": "process.hostdb.insert_duplicate_to_pending_dns",
        "method": "gauge",
    },
    "proxy.process.dns.lookup_avg_time": {"name": "process.dns.lookup_avg_time", "method": "gauge"},
    "proxy.process.dns.fail_avg_time": {"name": "process.dns.fail_avg_time", "method": "gauge"},
    "proxy.process.dns.tcp_retries": {"name": "process.dns.tcp_retries", "method": "gauge"},
    "proxy.process.dns.tcp_reset": {"name": "process.dns.tcp_reset", "method": "gauge"},
    "proxy.process.ssl.ssl_ocsp_refreshed_cert": {
        "name": "process.ssl.ocsp_refreshed_cert",
        "method": "gauge",
    },
    "proxy.process.ssl.ssl_ocsp_refresh_cert_failure": {
        "name": "process.ssl.ocsp_refresh_cert_failure",
        "method": "gauge",
    },
    "proxy.process.ssl.early_data_received": {"name": "process.ssl.early_data_received", "method": "gauge"},
    "proxy.node.config.reconfigure_time": {"name": "node.config.reconfigure_time", "method": "gauge"},
    "proxy.node.config.reconfigure_required": {
        "name": "node.config.reconfigure_required",
        "method": "gauge",
    },
    "proxy.node.config.restart_required.proxy": {
        "name": "node.config.restart_required.proxy",
        "method": "gauge",
    },
    "proxy.node.config.restart_required.manager": {
        "name": "node.config.restart_required.manager",
        "method": "gauge",
    },
    "proxy.node.config.draining": {"name": "node.config.draining", "method": "gauge"},
    "proxy.process.http.background_fill_current_count": {
        "name": "process.http.background_fill_current_count",
        "method": "gauge",
    },
    "proxy.process.http.current_client_connections": {
        "name": "process.http.current_client_connections",
        "method": "gauge",
    },
    "proxy.process.http.current_active_client_connections": {
        "name": "process.http.current_active_client_connections",
        "method": "gauge",
    },
    "proxy.process.http.websocket.current_active_client_connections": {
        "name": "process.http.websocket.current_active_client_connections",
        "method": "gauge",
    },
    "proxy.process.http.current_client_transactions": {
        "name": "process.http.current_client_transactions",
        "method": "gauge",
    },
    "proxy.process.http.current_server_transactions": {
        "name": "process.http.current_server_transactions",
        "method": "gauge",
    },
    "proxy.process.http.current_parent_proxy_connections": {
        "name": "process.http.current_parent_proxy_connections",
        "method": "gauge",
    },
    "proxy.process.http.current_server_connections": {
        "name": "process.http.current_server_connections",
        "method": "gauge",
    },
    "proxy.process.http.current_cache_connections": {
        "name": "process.http.current_cache_connections",
        "method": "gauge",
    },
    "proxy.process.http.pooled_server_connections": {
        "name": "process.http.pooled_server_connections",
        "method": "gauge",
    },
    "proxy.process.net.accepts_currently_open": {
        "name": "process.net.accepts_currently_open",
        "method": "gauge",
    },
    "proxy.process.net.connections_currently_open": {
        "name": "process.net.connections_currently_open",
        "method": "gauge",
    },
    "proxy.process.socks.connections_currently_open": {
        "name": "process.socks.connections_currently_open",
        "method": "gauge",
    },
    "proxy.process.cache.percent_full": {"name": "process.cache.percent_full", "method": "gauge"},
    "proxy.process.cache.direntries.total": {"name": "process.cache.direntries.total", "method": "gauge"},
    "proxy.process.cache.direntries.used": {"name": "process.cache.direntries.used", "method": "gauge"},
    "proxy.process.cache.directory_collision": {
        "name": "process.cache.directory_collision",
        "method": "gauge",
    },
    "proxy.process.cache.frags_per_doc.1": {"name": "process.cache.frags_per_doc.1", "method": "gauge"},
    "proxy.process.cache.frags_per_doc.2": {"name": "process.cache.frags_per_doc.2", "method": "gauge"},
    "proxy.process.cache.frags_per_doc.3+": {"name": "process.cache.frags_per_doc.3", "method": "gauge"},
    "proxy.process.cache.read_busy.success": {"name": "process.cache.read_busy.success", "method": "gauge"},
    "proxy.process.cache.read_busy.failure": {"name": "process.cache.read_busy.failure", "method": "gauge"},
    "proxy.process.cache.write_bytes_stat": {"name": "process.cache.write_bytes_stat", "method": "gauge"},
    "proxy.process.cache.vector_marshals": {"name": "process.cache.vector_marshals", "method": "gauge"},
    "proxy.process.cache.hdr_marshals": {"name": "process.cache.hdr_marshals", "method": "gauge"},
    "proxy.process.cache.hdr_marshal_bytes": {"name": "process.cache.hdr_marshal_bytes", "method": "gauge"},
    "proxy.process.cache.gc_bytes_evacuated": {
        "name": "process.cache.gc_bytes_evacuated",
        "method": "gauge",
    },
    "proxy.process.cache.gc_frags_evacuated": {
        "name": "process.cache.gc_frags_evacuated",
        "method": "gauge",
    },
    "proxy.process.cache.wrap_count": {"name": "process.cache.wrap_count", "method": "gauge"},
    "proxy.process.cache.sync.count": {"name": "process.cache.sync.count", "method": "gauge"},
    "proxy.process.cache.sync.bytes": {"name": "process.cache.sync.bytes", "method": "gauge"},
    "proxy.process.cache.sync.time": {"name": "process.cache.sync.time", "method": "gauge"},
    "proxy.process.cache.span.errors.read": {"name": "process.cache.span.errors.read", "method": "monotonic_count"},
    "proxy.process.cache.span.errors.write": {"name": "process.cache.span.errors.write", "method": "monotonic_count"},
    "proxy.process.cache.span.failing": {"name": "process.cache.span.failing", "method": "gauge"},
    "proxy.process.cache.span.offline": {"name": "process.cache.span.offline", "method": "gauge"},
    "proxy.process.cache.span.online": {"name": "process.cache.span.online", "method": "gauge"},
    "proxy.process.dns.success_avg_time": {"name": "process.dns.success_avg_time", "method": "gauge"},
    "proxy.process.dns.in_flight": {"name": "process.dns.in_flight", "method": "gauge"},
    "proxy.process.eventloop.count.10s": {"name": "process.eventloop.count.10s", "method": "gauge"},
    "proxy.process.eventloop.events.10s": {"name": "process.eventloop.events.10s", "method": "gauge"},
    "proxy.process.eventloop.events.min.10s": {
        "name": "process.eventloop.events.min.10s",
        "method": "gauge",
    },
    "proxy.process.eventloop.events.max.10s": {
        "name": "process.eventloop.events.max.10s",
        "method": "gauge",
    },
    "proxy.process.eventloop.wait.10s": {"name": "process.eventloop.wait.10s", "method": "gauge"},
    "proxy.process.eventloop.time.min.10s": {"name": "process.eventloop.time.min.10s", "method": "gauge"},
    "proxy.process.eventloop.time.max.10s": {"name": "process.eventloop.time.max.10s", "method": "gauge"},
    "proxy.process.eventloop.count.100s": {"name": "process.eventloop.count.100s", "method": "gauge"},
    "proxy.process.eventloop.events.100s": {"name": "process.eventloop.events.100s", "method": "gauge"},
    "proxy.process.eventloop.events.min.100s": {
        "name": "process.eventloop.events.min.100s",
        "method": "gauge",
    },
    "proxy.process.eventloop.events.max.100s": {
        "name": "process.eventloop.events.max.100s",
        "method": "gauge",
    },
    "proxy.process.eventloop.wait.100s": {"name": "process.eventloop.wait.100s", "method": "gauge"},
    "proxy.process.eventloop.time.min.100s": {"name": "process.eventloop.time.min.100s", "method": "gauge"},
    "proxy.process.eventloop.time.max.100s": {"name": "process.eventloop.time.max.100s", "method": "gauge"},
    "proxy.process.eventloop.count.1000s": {"name": "process.eventloop.count.1000s", "method": "gauge"},
    "proxy.process.eventloop.events.1000s": {"name": "process.eventloop.events.1000s", "method": "gauge"},
    "proxy.process.eventloop.events.min.1000s": {
        "name": "process.eventloop.events.min.1000s",
        "method": "gauge",
    },
    "proxy.process.eventloop.events.max.1000s": {
        "name": "process.eventloop.events.max.1000s",
        "method": "gauge",
    },
    "proxy.process.eventloop.wait.1000s": {"name": "process.eventloop.wait.1000s", "method": "gauge"},
    "proxy.process.eventloop.time.min.1000s": {
        "name": "process.eventloop.time.min.1000s",
        "method": "gauge",
    },
    "proxy.process.eventloop.time.max.1000s": {
        "name": "process.eventloop.time.max.1000s",
        "method": "gauge",
    },
    "proxy.process.traffic_server.memory.rss": {
        "name": "process.traffic_server.memory.rss",
        "method": "gauge",
    },
    "proxy.process.http2.current_client_connections": {
        "name": "process.http2.current_client_connections",
        "method": "gauge",
    },
    "proxy.process.http2.current_active_client_connections": {
        "name": "process.http2.current_active_client_connections",
        "method": "gauge",
    },
    "proxy.process.http2.current_client_streams": {
        "name": "process.http2.current_client_streams",
        "method": "gauge",
    },
    "proxy.process.hostdb.cache.current_items": {
        "name": "process.hostdb.cache.current_items",
        "method": "gauge",
    },
    "proxy.process.hostdb.cache.current_size": {
        "name": "process.hostdb.cache.current_size",
        "method": "gauge",
    },
    "proxy.process.hostdb.cache.last_sync.time": {
        "name": "process.hostdb.cache.last_sync.time",
        "method": "gauge",
    },
    "proxy.process.hostdb.cache.last_sync.total_items": {
        "name": "process.hostdb.cache.last_sync.total_items",
        "method": "gauge",
    },
    "proxy.process.hostdb.cache.last_sync.total_size": {
        "name": "process.hostdb.cache.last_sync.total_size",
        "method": "gauge",
    },
    "proxy.process.log.log_files_open": {"name": "process.log.log_files_open", "method": "gauge"},
    "proxy.process.log.log_files_space_used": {
        "name": "process.log.log_files_space_used",
        "method": "gauge",
    },
}

REGEX_METRICS = [
    {
        'regex': r'proxy\.process\.ssl\.cipher\.user_agent\.(.*)',
        'name': 'process.ssl.cipher.user_agent',
        'tags': ('cipher',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.http\.(1[0-9]{2})_responses',
        'name': 'process.http.code.1xx_responses',
        'tags': ('code',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.http\.(2[0-9]{2})_responses',
        'name': 'process.http.code.2xx_responses',
        'tags': ('code',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.http\.(3[0-9]{2})_responses',
        'name': 'process.http.code.3xx_responses',
        'tags': ('code',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.http\.(4[0-9]{2})_responses',
        'name': 'process.http.code.4xx_responses',
        'tags': ('code',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.http\.(5[0-9]{2})_responses',
        'name': 'process.http.code.5xx_responses',
        'tags': ('code',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.([A-Za-z0-9_-]*)\.bytes_used',
        'name': 'process.cache.volume.bytes_used',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.bytes_total',
        'name': 'process.cache.volume.bytes_total',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.ram_cache\.total_bytes',
        'name': 'process.cache.volume.ram_cache.total_bytes',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.ram_cache\.bytes_used',
        'name': 'process.cache.volume.ram_cache.bytes_used',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.ram_cache\.hits',
        'name': 'process.cache.volume.ram_cache.hits',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.ram_cache\.misses',
        'name': 'process.cache.volume.ram_cache.misses',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.pread_count',
        'name': 'process.cache.volume.pread_count',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.percent_full',
        'name': 'process.cache.volume.percent_full',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.lookup\.active',
        'name': 'process.cache.volume.lookup.active',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.lookup\.success',
        'name': 'process.cache.volume.lookup.success',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.lookup\.failure',
        'name': 'process.cache.volume.lookup.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.read\.active',
        'name': 'process.cache.volume.read.active',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.read\.success',
        'name': 'process.cache.volume.read.success',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.read\.failure',
        'name': 'process.cache.volume.read.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.write\.active',
        'name': 'process.cache.volume.write.active',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.write\.success',
        'name': 'process.cache.volume.write.success',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.write\.failure',
        'name': 'process.cache.volume.write.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.write\.backlog\.failure',
        'name': 'process.cache.volume.write.backlog.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.update\.active',
        'name': 'process.cache.volume.update.active',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.update\.success',
        'name': 'process.cache.volume.update.success',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.update\.failure',
        'name': 'process.cache.volume.update.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.remove\.active',
        'name': 'process.cache.volume.remove.active',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.remove\.success',
        'name': 'process.cache.volume.remove.success',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.remove\.failure',
        'name': 'process.cache.volume.remove.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.evacuate\.active',
        'name': 'process.cache.volume.evacuate.active',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.evacuate\.success',
        'name': 'process.cache.volume.evacuate.success',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.evacuate\.failure',
        'name': 'process.cache.volume.evacuate.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.scan\.active',
        'name': 'process.cache.volume.scan.active',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.scan\.success',
        'name': 'process.cache.volume.scan.success',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.scan\.failure',
        'name': 'process.cache.volume.scan.failure',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.direntries\.total',
        'name': 'process.cache.volume.direntries.total',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.direntries\.used',
        'name': 'process.cache.volume.direntries.used',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.directory_collision',
        'name': 'process.cache.volume.directory_collision',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.frags_per_doc\.1',
        'name': 'process.cache.volume.frags_per_doc.1',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.frags_per_doc\.2',
        'name': 'process.cache.volume.frags_per_doc.2',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.frags_per_doc\.3\+',
        'name': 'process.cache.volume.frags_per_doc.3',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.read_busy\.success',
        'name': 'process.cache.volume.read_busy.success',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.read_busy\.failure',
        'name': 'process.cache.volume.read_busy.failure',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.write_bytes_stat',
        'name': 'process.cache.volume.write_bytes_stat',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.vector_marshals',
        'name': 'process.cache.volume.vector_marshals',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.hdr_marshals',
        'name': 'process.cache.volume.hdr_marshals',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.hdr_marshal_bytes',
        'name': 'process.cache.volume.hdr_marshal_bytes',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.gc_bytes_evacuated',
        'name': 'process.cache.volume.gc_bytes_evacuated',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.gc_frags_evacuated',
        'name': 'process.cache.volume.gc_frags_evacuated',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.sync\.count',
        'name': 'process.cache.volume.sync.count',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.sync\.bytes',
        'name': 'process.cache.volume.sync.bytes',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.sync\.time',
        'name': 'process.cache.volume.sync.time',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.span\.errors\.read',
        'name': 'process.cache.volume.span.errors.read',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.span\.errors\.write',
        'name': 'process.cache.volume.span.errors.write',
        'tags': ('cache_volume',),
        'method': 'monotonic_count',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.span\.failing',
        'name': 'process.cache.volume.span.failing',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.span\.offline',
        'name': 'process.cache.volume.span.offline',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
    {
        'regex': r'proxy\.process\.cache\.(.*?)\.span\.online',
        'name': 'process.cache.volume.span.online',
        'tags': ('cache_volume',),
        'method': 'gauge',
    },
]


def build_metric(metric_name, logger):
    # type: (str, Any) -> Tuple[Optional[str], Optional[List[str]]]
    """
    proxy.node.restarts.proxy.restart_count
    proxy.process.cache.volume_1.span.offline
    proxy.process.http.101_responses
    """
    additional_tags = []
    name = metric_name
    method = 'gauge'

    if metric_name in SIMPLE_METRICS:
        metric_mapping = SIMPLE_METRICS[metric_name]
        name = metric_mapping['name']
        method = metric_mapping['method']

    else:
        for regex in REGEX_METRICS:
            tags_values = []
            results = re.findall(str(regex['regex']), metric_name)

            if len(results) > 0 and isinstance(results[0], tuple):
                tags_values = list(results[0])
            else:
                tags_values = results

            if len(tags_values) == len(regex['tags']):
                method = regex['method']
                name = str(regex['name'])
                for i in range(len(regex['tags'])):
                    additional_tags.append('{}:{}'.format(regex['tags'][i], tags_values[i]))
                break
        else:
            logger.debug('Ignoring metric %s', metric_name)
            return None, [], method

    logger.debug('Found metric %s (%s)', name, metric_name)

    return name, additional_tags, method
