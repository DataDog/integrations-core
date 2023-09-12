# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()
UI_PORT = "8983"

SOLR_METRICS = [
    "solr.document_cache.evictions",
    "solr.document_cache.hits",
    "solr.document_cache.inserts",
    "solr.document_cache.lookups",
    "solr.filter_cache.evictions",
    "solr.filter_cache.hits",
    "solr.filter_cache.inserts",
    "solr.filter_cache.lookups",
    "solr.query_result_cache.evictions",
    "solr.query_result_cache.hits",
    "solr.query_result_cache.inserts",
    "solr.query_result_cache.lookups",
    "solr.search_handler.errors",
    "solr.search_handler.request_times.50percentile",
    "solr.search_handler.request_times.75percentile",
    "solr.search_handler.request_times.95percentile",
    "solr.search_handler.request_times.98percentile",
    "solr.search_handler.request_times.99percentile",
    "solr.search_handler.request_times.999percentile",
    "solr.search_handler.request_times.mean",
    "solr.search_handler.request_times.mean_rate",
    "solr.search_handler.request_times.one_minute_rate",
    "solr.search_handler.requests",
    "solr.search_handler.time",
    "solr.search_handler.timeouts",
    "solr.searcher.maxdocs",
    "solr.searcher.numdocs",
    "solr.searcher.warmup",
]
