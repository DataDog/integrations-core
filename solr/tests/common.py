# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from packaging import version

from datadog_checks.dev import get_docker_hostname

HOST = get_docker_hostname()
SOLR_VERSION_RAW = os.environ['SOLR_VERSION']
SOLR_VERSION = version.parse(SOLR_VERSION_RAW)

SOLR_COMMON_METRICS = [
    "solr.search_handler.errors",
    "solr.search_handler.requests",
    "solr.search_handler.time",
    "solr.search_handler.timeouts",
    "solr.searcher.numdocs",
    "solr.searcher.warmup",
]

SOLR_7_PLUS_METRICS = [
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
    "solr.search_handler.request_times.50percentile",
    "solr.search_handler.request_times.75percentile",
    "solr.search_handler.request_times.95percentile",
    "solr.search_handler.request_times.98percentile",
    "solr.search_handler.request_times.99percentile",
    "solr.search_handler.request_times.999percentile",
    "solr.search_handler.request_times.mean",
    "solr.search_handler.request_times.mean_rate",
    "solr.search_handler.request_times.one_minute_rate",
    "solr.searcher.maxdocs",
]

SOLR_6_METRICS = [
    "solr.cache.evictions",
    "solr.cache.hits",
    "solr.cache.inserts",
    "solr.cache.lookups",
    "solr.search_handler.avg_time_per_req",
    "solr.search_handler.avg_requests_per_sec",
    "solr.searcher.maxdoc",
]


if SOLR_VERSION.major == 6:
    SOLR_METRICS = SOLR_COMMON_METRICS + SOLR_6_METRICS
elif SOLR_VERSION.major >= 7:
    SOLR_METRICS = SOLR_COMMON_METRICS + SOLR_7_PLUS_METRICS
else:
    raise Exception('Version not supported: {}'.format(SOLR_VERSION))
