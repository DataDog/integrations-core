# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_here
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW

CHECK_NAME = "tomcat"

HERE = get_here()

TOMCAT_E2E_METRICS = [
    # Tomcat
    "tomcat.max_time",
    "tomcat.threads.busy",
    "tomcat.threads.count",
    "tomcat.threads.max",
    # Rates
    "tomcat.bytes_sent",
    "tomcat.bytes_rcvd",
    "tomcat.error_count",
    "tomcat.request_count",
    "tomcat.processing_time",
    "tomcat.servlet.processing_time",
    "tomcat.servlet.error_count",
    "tomcat.servlet.request_count",
    "tomcat.jsp.count",
    "tomcat.jsp.reload_count",
    "tomcat.string_cache.access_count",
    "tomcat.string_cache.hit_count",
    "tomcat.web.cache.hit_count",
    "tomcat.web.cache.lookup_count",
] + JVM_E2E_METRICS_NEW
