# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.utils import get_tox_env

from .common import EXPECTED_METRICS, EXPECTED_TAGS, SERVICE_CHECK_CONNECT, SERVICE_CHECK_QUERY, TERADATA_SERVER

TOX_ENV = get_tox_env()
ON_CI = running_on_ci()
skip_on_ci = pytest.mark.skipif(
    ON_CI and TOX_ENV != 'py38-sandbox', reason='Do not run E2E test on sandbox environment'
)


@pytest.mark.skipif(TOX_ENV == 'py38-sandbox', reason='Test only available for py38 environment')
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception, match="ModuleNotFoundError: No module named 'teradatasql'"):
        dd_agent_check(instance)
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, count=1, tags=EXPECTED_TAGS)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, count=0)


@pytest.mark.skipif(TOX_ENV != 'py38-sandbox', reason='Test only available for py38 sandbox environment')
@pytest.mark.e2e
def test_e2e_sandbox(dd_agent_check, aggregator, instance):
    global_tags = ['teradata_port:1025', 'teradata_server:{}'.format(TERADATA_SERVER)]
    disk_tag_prefixes = ['td_account', 'td_database', 'td_table']
    amp_tag_prefixes = ['td_account', 'td_user']

    aggregator = dd_agent_check()

    for metric in EXPECTED_METRICS:
        if 'teradata.disk_space' in metric:
            aggregator.assert_metric(metric, at_least=1)
            for prefix in disk_tag_prefixes:
                aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)
        elif 'teradata.amp' in metric:
            aggregator.assert_metric(metric, at_least=1)
            for prefix in amp_tag_prefixes:
                aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)
        else:
            # assert at_least=0 to account for potential clock drift in the sandbox VM
            aggregator.assert_metric(metric, at_least=0, tags=global_tags)
        for tag in global_tags:
            aggregator.assert_metric_has_tag(metric, tag)
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, count=1, tags=global_tags)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.OK, at_least=0, tags=global_tags)
