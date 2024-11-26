# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://docs.aerospike.com/server/operations/monitor/key_metrics
METRIC_MAP = {
    # all metrics ( except latencies), will be treated as gauge, as we need latest values, without having up-down changes
    "aerospike_users(.*)": {"name": "$1", "type": "gauge"},
    "aerospike_namespace(.*)": {"name": "$1", "type": "gauge"},
    "aerospike_node(.*)": {"name": "$1", "type": "gauge"},
    "aerospike_sets(.*)": {"name": "$1", "type": "gauge"},
    "aerospike_sindex(.*)": {"name": "$1", "type": "gauge"},
    "aerospike_xdr(.*)": {"name": "$1", "type": "gauge"},
    "aerospike_sysinfo(.*)": {"name": "$1", "type": "gauge"},
    
    # all latency metrics will be treated as Distribution in datadog cloud    
    "aerospike_latencies(.*)": {"name": "$1", "type": "histogram"},    
}

