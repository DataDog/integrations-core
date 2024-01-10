# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics

from .common import TOMCAT_E2E_METRICS

COUNTER_METRICS = [
    # TODO: JMXFetch is not reporting in-app type for JMX `counter` type.
    #       Remove this exclusion list when fixed.
    'tomcat.bytes_rcvd',
    'tomcat.bytes_sent',
    'tomcat.error_count',
    'tomcat.jsp.count',
    'tomcat.jsp.reload_count',
    'tomcat.processing_time',
    'tomcat.request_count',
    'tomcat.servlet.error_count',
    'tomcat.servlet.processing_time',
    'tomcat.servlet.request_count',
    'tomcat.string_cache.access_count',
    'tomcat.string_cache.hit_count',
    'tomcat.web.cache.hit_count',
    'tomcat.web.cache.lookup_count',
]


def test_metrics(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in TOMCAT_E2E_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'instance:tomcat-localhost-9012')
        aggregator.assert_metric_has_tag(metric, 'dd.internal.jmx_check_name:tomcat')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW + COUNTER_METRICS)


def test_service_checks(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_service_check(
        "tomcat.can_connect", status=AgentCheck.OK, tags=['instance:tomcat-localhost-9012', 'jmx_server:localhost']
    )
