# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import (
    DEFAULT_METRICS,
    E2E_EXCLUDE_METRICS,
    EXPECTED_TAGS,
    ON_CI,
    RES_USAGE_METRICS,
    SERVICE_CHECK_CONNECT,
    SERVICE_CHECK_QUERY,
    TABLE_DISK_METRICS,
    TERADATA_SERVER,
    USE_TD_SANDBOX,
)

skip_on_ci = pytest.mark.skipif(ON_CI and not USE_TD_SANDBOX, reason='Do not run E2E test on sandbox environment')


@pytest.mark.skipif(USE_TD_SANDBOX, reason='Test only available for non-sandbox environments')
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception, match="Hostname lookup failed"):
        dd_agent_check(instance)
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, count=1, tags=EXPECTED_TAGS)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, count=0)


@pytest.mark.skipif(not USE_TD_SANDBOX, reason='Test only available for sandbox environments')
@pytest.mark.e2e
def test_e2e_sandbox(dd_agent_check, aggregator, instance):
    global_tags = ['teradata_port:1025', 'teradata_server:{}'.format(TERADATA_SERVER)]
    disk_tag_prefixes = ['td_amp', 'td_account', 'td_database']
    table_disk_tag_prefixes = ['td_amp', 'td_account', 'td_database', 'td_table']
    amp_tag_prefixes = ['td_amp', 'td_account', 'td_user']

    aggregator = dd_agent_check()

    for metric in DEFAULT_METRICS:
        if metric not in E2E_EXCLUDE_METRICS:
            aggregator.assert_metric(metric, at_least=1)
            if 'teradata.disk_space' in metric:
                for prefix in disk_tag_prefixes:
                    aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)
            elif 'teradata.amp' in metric:
                for prefix in amp_tag_prefixes:
                    aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)

    for metric in RES_USAGE_METRICS:
        if metric not in E2E_EXCLUDE_METRICS:
            # assert at_least=0 to account for potential clock drift in the sandbox VM
            aggregator.assert_metric(metric, at_least=0, tags=global_tags)

    for metric in TABLE_DISK_METRICS:
        if metric not in E2E_EXCLUDE_METRICS:
            aggregator.assert_metric(metric, at_least=1)
            for prefix in table_disk_tag_prefixes:
                aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)

    for tag in global_tags:
        aggregator.assert_metric_has_tag(metric, tag, at_least=1)

    # assert can_query service check at_least=0 to account for potential clock drift in sandbox VM
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, count=1, tags=global_tags)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.OK, at_least=0, tags=global_tags)
