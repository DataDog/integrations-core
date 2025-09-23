# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW

CHECK_NAME = "tomcat"
PORT = "8080"

HELLO_URL = f"http://{get_docker_hostname()}:{PORT}/sample/hello.jsp"
FLAVOR = os.environ.get('FLAVOR')
HERE = get_here()

TOMCAT_E2E_METRICS = [
    "tomcat.max_time",
    "tomcat.threads.busy",
    "tomcat.threads.count",
    "tomcat.threads.max",
    "tomcat.threads.min",
    "tomcat.bytes_sent",
    "tomcat.bytes_rcvd",
    "tomcat.error_count",
    "tomcat.request_count",
    "tomcat.processing_time",
    "tomcat.servlet.processing_time",
    "tomcat.servlet.error_count",
    "tomcat.servlet.request_count",
    "tomcat.servlet.max_time",
    "tomcat.servlet.min_time",
    "tomcat.jsp.count",
    "tomcat.jsp.reload_count",
    "tomcat.string_cache.access_count",
    "tomcat.string_cache.hit_count",
    "tomcat.string_cache.size",
    "tomcat.string_cache.max_size",
    "tomcat.web.cache.hit_count",
    "tomcat.web.cache.lookup_count",
]

TOMCAT_E2E_METRICS += JVM_E2E_METRICS_NEW

JDBC_METRICS = [
    "tomcat.jdbc.connection_pool.active",
    "tomcat.jdbc.connection_pool.max_active",
    "tomcat.jdbc.connection_pool.idle",
    "tomcat.jdbc.connection_pool.max_idle",
    "tomcat.jdbc.connection_pool.min_idle",
    "tomcat.jdbc.connection_pool.size",
]

if FLAVOR == 'standalone':
    TOMCAT_E2E_METRICS += JDBC_METRICS

OPTIONAL_TOMCAT_E2E_METRICS = [
    "tomcat.min_time",
    "tomcat.string_cache.size",
    "tomcat.string_cache.max_size",
]

E2E_METADATA = {
    'use_jmx': True,
    'env_vars': {
        'DD_LOGS_ENABLED': 'true',
    },
}
