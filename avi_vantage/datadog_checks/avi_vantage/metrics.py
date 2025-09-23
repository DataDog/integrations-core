# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

VIRTUAL_SERVICE_METRICS = {
    # The following commented metrics are documented but don't seem to be available.
    # "dns_client.avg_avi_errors": {
    #     "name": "dns_client.avg_avi_errors",
    #     "type": "gauge",
    # },
    # "dns_client.avg_complete_queries": {
    #     "name": "dns_client.avg_complete_queries",
    #     "type": "gauge",
    # },
    # "dns_client.avg_domain_lookup_failures": {
    #     "name": "dns_client.avg_domain_lookup_failures",
    #     "type": "gauge",
    # },
    # "dns_client.avg_tcp_queries": {
    #     "name": "dns_client.avg_tcp_queries",
    #     "type": "gauge",
    # },
    # "dns_client.avg_udp_passthrough_resp_time": {
    #     "name": "dns_client.avg_udp_passthrough_resp_time",
    #     "type": "gauge",
    # },
    # "dns_client.avg_udp_queries": {
    #     "name": "dns_client.avg_udp_queries",
    #     "type": "gauge",
    # },
    # "dns_client.avg_unsupported_queries": {
    #     "name": "dns_client.avg_unsupported_queries",
    #     "type": "gauge",
    # },
    # "dns_client.pct_errored_queries": {
    #     "name": "dns_client.pct_errored_queries",
    #     "type": "gauge",
    # },
    # "dns_server.avg_complete_queries": {
    #     "name": "dns_server.avg_complete_queries",
    #     "type": "gauge",
    # },
    # "dns_server.avg_errored_queries": {
    #     "name": "dns_server.avg_errored_queries",
    #     "type": "gauge",
    # },
    # "dns_server.avg_tcp_queries": {
    #     "name": "dns_server.avg_tcp_queries",
    #     "type": "gauge",
    # },
    # "dns_server.avg_udp_queries": {
    #     "name": "dns_server.avg_udp_queries",
    #     "type": "gauge",
    # },
    "avi_healthscore_health_score_value": {
        "name": "virtual_service_healthscore",
        "type": "gauge",
    },
    "avi_l4_client_apdexc": {
        "name": "l4_client.apdexc",
        "type": "gauge",
    },
    "avi_l4_client_avg_application_dos_attacks": {
        "name": "l4_client.avg_application_dos_attacks",
        "type": "gauge",
    },
    "avi_l4_client_avg_bandwidth": {
        "name": "l4_client.avg_bandwidth",
        "type": "gauge",
    },
    "avi_l4_client_avg_complete_conns": {
        "name": "l4_client.avg_complete_conns",
        "type": "gauge",
    },
    "avi_l4_client_avg_connections_dropped": {
        "name": "l4_client.avg_connections_dropped",
        "type": "gauge",
    },
    "avi_l4_client_avg_lossy_connections": {
        "name": "l4_client.avg_lossy_connections",
        "type": "gauge",
    },
    "avi_l4_client_avg_new_established_conns": {
        "name": "l4_client.avg_new_established_conns",
        "type": "gauge",
    },
    "avi_l4_client_avg_policy_drops": {
        "name": "l4_client.avg_policy_drops",
        "type": "gauge",
    },
    "avi_l4_client_avg_rx_bytes": {
        "name": "l4_client.avg_rx_bytes",
        "type": "gauge",
    },
    "avi_l4_client_avg_rx_pkts": {
        "name": "l4_client.avg_rx_pkts",
        "type": "gauge",
    },
    "avi_l4_client_sum_end_to_end_rtt": {
        "name": "l4_client.sum_end_to_end_rtt",
        "type": "gauge",
    },
    "avi_l4_client_avg_tx_bytes": {
        "name": "l4_client.avg_tx_bytes",
        "type": "gauge",
    },
    "avi_l4_client_avg_tx_pkts": {
        "name": "l4_client.avg_tx_pkts",
        "type": "gauge",
    },
    "avi_l4_client_max_open_conns": {
        "name": "l4_client.max_open_conns",
        "type": "gauge",
    },
    "avi_l7_client_apdexr": {
        "name": "l7_client.apdexr",
        "type": "gauge",
    },
    "avi_l7_client_sum_client_data_transfer_time": {
        "name": "l7_client.sum_client_data_transfer_time",
        "type": "gauge",
    },
    "avi_l7_client_avg_client_txn_latency": {
        "name": "l7_client.avg_client_txn_latency",
        "type": "gauge",
    },
    "avi_l7_client_avg_complete_responses": {
        "name": "l7_client.avg_complete_responses",
        "type": "gauge",
    },
    "avi_l7_client_avg_error_responses": {
        "name": "l7_client.avg_error_responses",
        "type": "gauge",
    },
    "avi_l7_client_avg_frustrated_responses": {
        "name": "l7_client.avg_frustrated_responses",
        "type": "gauge",
    },
    "avi_l7_client_sum_http_headers_bytes": {
        "name": "l7_client.sum_http_headers_bytes",
        "type": "gauge",
    },
    "avi_l7_client_sum_http_headers_count": {
        "name": "l7_client.sum_http_headers_count",
        "type": "gauge",
    },
    "avi_l7_client_sum_http_params_count": {
        "name": "l7_client.sum_http_params_count",
        "type": "gauge",
    },
    "avi_l7_client_sum_page_load_time": {
        "name": "l7_client.sum_page_load_time",
        "type": "gauge",
    },
    "avi_l7_client_sum_post_bytes": {
        "name": "l7_client.sum_post_bytes",
        "type": "gauge",
    },
    "avi_l7_client_avg_resp_2xx": {
        "name": "l7_client.avg_resp_2xx",
        "type": "gauge",
    },
    "avi_l7_client_avg_resp_4xx": {
        "name": "l7_client.avg_resp_4xx",
        "type": "gauge",
    },
    "avi_l7_client_avg_resp_4xx_avi_errors": {
        "name": "l7_client.avg_resp_4xx_avi_errors",
        "type": "gauge",
    },
    "avi_l7_client_avg_resp_5xx": {
        "name": "l7_client.avg_resp_5xx",
        "type": "gauge",
    },
    "avi_l7_client_avg_resp_5xx_avi_errors": {
        "name": "l7_client.avg_resp_5xx_avi_errors",
        "type": "gauge",
    },
    "avi_l7_client_avg_ssl_connections": {
        "name": "l7_client.avg_ssl_connections",
        "type": "gauge",
    },
    "avi_l7_client_avg_ssl_handshakes_new": {
        "name": "l7_client.avg_ssl_handshakes_new",
        "type": "gauge",
    },
    "avi_l7_client_avg_ssl_errors": {
        "name": "l7_client.avg_ssl_errors",
        "type": "gauge",
    },
    "avi_l7_client_sum_uri_length": {
        "name": "l7_client.sum_uri_length",
        "type": "gauge",
    },
    "avi_l7_client_avg_waf_attacks": {
        "name": "l7_client.avg_waf_attacks",
        "type": "gauge",
    },
    "avi_l7_client_avg_waf_disabled": {
        "name": "l7_client.avg_waf_disabled",
        "type": "gauge",
    },
    "avi_l7_client_avg_waf_evaluated": {
        "name": "l7_client.avg_waf_evaluated",
        "type": "gauge",
    },
    "avi_l7_client_avg_waf_matched": {
        "name": "l7_client.avg_waf_matched",
        "type": "gauge",
    },
    "avi_l7_client_avg_waf_rejected": {
        "name": "l7_client.avg_waf_rejected",
        "type": "gauge",
    },
    "avi_l7_client_pct_get_reqs": {
        "name": "l7_client.pct_get_reqs",
        "type": "gauge",
    },
    "avi_l7_client_pct_post_reqs": {
        "name": "l7_client.pct_post_reqs",
        "type": "gauge",
    },
    "avi_l7_client_pct_waf_attacks": {
        "name": "l7_client.pct_waf_attacks",
        "type": "gauge",
    },
    "avi_l7_client_pct_waf_disabled": {
        "name": "l7_client.pct_waf_disabled",
        "type": "gauge",
    },
    "avi_l7_client_sum_application_response_time": {
        "name": "l7_client.sum_application_response_time",
        "type": "gauge",
    },
    "avi_l7_client_sum_get_reqs": {
        "name": "l7_client.sum_get_reqs",
        "type": "gauge",
    },
    "avi_l7_client_sum_other_reqs": {
        "name": "l7_client.sum_other_reqs",
        "type": "gauge",
    },
    "avi_l7_client_sum_post_reqs": {
        "name": "l7_client.sum_post_reqs",
        "type": "gauge",
    },
    "avi_l7_client_sum_total_responses": {
        "name": "l7_client.sum_total_responses",
        "type": "gauge",
    },
    "avi_l7_client_pct_response_errors": {
        "name": "l7_client.pct_response_errors",
        "type": "gauge",
    },
}

POOL_METRICS = {
    "avi_healthscore_health_score_value": {
        "name": "pool_healthscore",
        "type": "gauge",
    },
    # "avi_l4_server_apdexc": {
    #     "name": "l4_server.apdexc",
    #     "type": "gauge",
    # },
    "avi_l4_server_avg_bandwidth": {
        "name": "l4_server.avg_bandwidth",
        "type": "gauge",
    },
    "avi_l4_server_avg_errored_connections": {
        "name": "l4_server.avg_errored_connections",
        "type": "gauge",
    },
    "avi_l4_server_avg_new_established_conns": {
        "name": "l4_server.avg_new_established_conns",
        "type": "gauge",
    },
    "avi_l4_server_avg_open_conns": {
        "name": "l4_server.avg_open_conns",
        "type": "gauge",
    },
    "avi_l4_server_avg_pool_complete_conns": {
        "name": "l4_server.avg_pool_complete_conns",
        "type": "gauge",
    },
    "avi_l4_server_avg_pool_open_conns": {
        "name": "l4_server.avg_pool_open_conns",
        "type": "gauge",
    },
    "avi_l4_server_avg_rx_bytes": {
        "name": "l4_server.avg_rx_bytes",
        "type": "gauge",
    },
    "avi_l4_server_avg_rx_pkts": {
        "name": "l4_server.avg_rx_pkts",
        "type": "gauge",
    },
    "avi_l4_server_sum_rtt": {
        "name": "l4_server.sum_rtt",
        "type": "gauge",
    },
    "avi_l4_server_avg_tx_bytes": {
        "name": "l4_server.avg_tx_bytes",
        "type": "gauge",
    },
    "avi_l4_server_avg_tx_pkts": {
        "name": "l4_server.avg_tx_pkts",
        "type": "gauge",
    },
    "avi_l4_server_max_open_conns": {
        "name": "l4_server.max_open_conns",
        "type": "gauge",
    },
    #  "avi_l7_server_apdexr": {
    #     "name": "l7_server.apdexr",
    #     "type": "gauge",
    # },
    "avi_l7_server_sum_application_response_time": {
        "name": "l7_server.sum_application_response_time",
        "type": "gauge",
    },
    "avi_l7_server_avg_complete_responses": {
        "name": "l7_server.avg_complete_responses",
        "type": "gauge",
    },
    "avi_l7_server_avg_frustrated_responses": {
        "name": "l7_server.avg_frustrated_responses",
        "type": "gauge",
    },
    "avi_l7_server_sum_other_resp_latency": {
        "name": "l7_server.sum_other_resp_latency",
        "type": "gauge",
    },
    "avi_l7_server_sum_get_resp_latency": {
        "name": "l7_server.sum_get_resp_latency",
        "type": "gauge",
    },
    "avi_l7_server_sum_post_resp_latency": {
        "name": "l7_server.sum_post_resp_latency",
        "type": "gauge",
    },
    "avi_l7_server_avg_total_requests": {
        "name": "l7_server.avg_total_requests",
        "type": "gauge",
    },
    "avi_l7_server_avg_error_responses": {
        "name": "l7_server.avg_error_responses",
        "type": "gauge",
    },
    "avi_l7_server_avg_resp_4xx": {
        "name": "l7_server.avg_resp_4xx",
        "type": "gauge",
    },
    "avi_l7_server_avg_resp_5xx": {
        "name": "l7_server.avg_resp_5xx",
        "type": "gauge",
    },
}

SERVICE_ENGINE_METRICS = {
    "avi_healthscore_health_score_value": {
        "name": "service_engine_healthscore",
        "type": "gauge",
    },
    # "se_if.avg_bandwidth": {
    #     "name": "se_if.avg_bandwidth",
    #     "type": "gauge",
    # },
    # "se_if.avg_connection_table_usage": {
    #     "name": "se_if.avg_connection_table_usage",
    #     "type": "gauge",
    # },
    # "se_if.avg_rx_bytes": {
    #     "name": "se_if.avg_rx_bytes",
    #     "type": "gauge",
    # },
    # "se_if.avg_rx_pkts": {
    #     "name": "se_if.avg_rx_pkts",
    #     "type": "gauge",
    # },
    # "se_if.avg_rx_pkts_dropped_non_vs": {
    #     "name": "se_if.avg_rx_pkts_dropped_non_vs",
    #     "type": "gauge",
    # },
    # "se_if.avg_tx_bytes": {
    #     "name": "se_if.avg_tx_bytes",
    #     "type": "gauge",
    # },
    # "se_if.avg_tx_pkts": {
    #     "name": "se_if.avg_tx_pkts",
    #     "type": "gauge",
    # },
    "avi_se_stats_avg_connection_mem_usage": {
        "name": "se_stats.avg_connection_mem_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_connections": {
        "name": "se_stats.avg_connections",
        "type": "gauge",
    },
    "avi_se_stats_avg_connections_dropped": {
        "name": "se_stats.avg_connections_dropped",
        "type": "gauge",
    },
    "avi_se_stats_avg_cpu_usage": {
        "name": "se_stats.avg_cpu_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_disk1_usage": {
        "name": "se_stats.avg_disk1_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_dynamic_mem_usage": {
        "name": "se_stats.avg_dynamic_mem_usage",
        "type": "gauge",
    },
    #  "avi_se_stats_avg_eth0_bandwidth": {
    #     "name": "se_stats.avg_eth0_bandwidth",
    #     "type": "gauge",
    # },
    "avi_se_stats_avg_mem_usage": {
        "name": "se_stats.avg_mem_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_packet_buffer_header_usage": {
        "name": "se_stats.avg_packet_buffer_header_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_packet_buffer_large_usage": {
        "name": "se_stats.avg_packet_buffer_large_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_packet_buffer_small_usage": {
        "name": "se_stats.avg_packet_buffer_small_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_packet_buffer_usage": {
        "name": "se_stats.avg_packet_buffer_usage",
        "type": "gauge",
    },
    "avi_se_stats_avg_persistent_table_usage": {
        "name": "se_stats.avg_persistent_table_usage",
        "type": "gauge",
    },
    # "avi_se_stats_avg_rx_bandwidth": {
    #     "name": "se_stats.avg_rx_bandwidth",
    #     "type": "gauge",
    # },
    # "avi_se_stats_avg_ssl_session_cache_usage": {
    #     "name": "se_stats.avg_ssl_session_cache_usage",
    #     "type": "gauge",
    # },
    "avi_se_stats_avg_ssl_session_cache": {
        "name": "se_stats.avg_ssl_session_cache",
        "type": "gauge",
    },
    # "avi_se_stats_max_se_bandwidth": {
    #     "name": "se_stats.max_se_bandwidth",
    #     "type": "gauge",
    # },
    "avi_se_stats_pct_syn_cache_usage": {
        "name": "se_stats.pct_syn_cache_usage",
        "type": "gauge",
    },
}

CONTROLLER_METRICS = {
    "avi_controller_stats_avg_cpu_usage": {
        "name": "controller_stats.avg_cpu_usage",
        "type": "gauge",
    },
    "avi_controller_stats_avg_disk_usage": {
        "name": "controller_stats.avg_disk_usage",
        "type": "gauge",
    },
    "avi_controller_stats_avg_mem_usage": {
        "name": "controller_stats.avg_mem_usage",
        "type": "gauge",
    },
    "avi_controller_stats_avg_disk_write_bytes": {
        "name": "controller_stats.avg_disk_write_bytes",
        "type": "gauge",
    },
}
