# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics

from .common import OPTIONAL_TOMCAT_E2E_METRICS, TOMCAT_E2E_METRICS


def test_metrics(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in TOMCAT_E2E_METRICS:
        at_least = 0 if metric in OPTIONAL_TOMCAT_E2E_METRICS else 1
        aggregator.assert_metric(metric, at_least=at_least)

        if at_least:
            aggregator.assert_metric_has_tag(metric, 'instance:tomcat-localhost-9012')
            aggregator.assert_metric_has_tag(metric, 'dd.internal.jmx_check_name:tomcat')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)


def test_service_checks(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_service_check(
        "tomcat.can_connect", status=AgentCheck.OK, tags=['instance:tomcat-localhost-9012', 'jmx_server:localhost']
    )
