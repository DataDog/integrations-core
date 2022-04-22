# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.teradata import TeradataCheck

from .common import CHECK_NAME, SERVICE_CHECK_CONNECT, SERVICE_CHECK_QUERY


def test_check(cursor_factory, aggregator, instance, dd_run_check, expected_metrics):
    with cursor_factory():
        check = TeradataCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(
            metric['name'],
            metric['value'],
            sorted(metric['tags'] + ['td_env:dev']),
            count=1,
            metric_type=metric['type'],
        )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_service_check(
        SERVICE_CHECK_CONNECT,
        ServiceCheck.OK,
        tags=['teradata_server:tdserver', 'teradata_port:1025', 'td_env:dev'],
    )
    aggregator.assert_service_check(
        SERVICE_CHECK_QUERY,
        ServiceCheck.OK,
        tags=['teradata_server:tdserver', 'teradata_port:1025', 'td_env:dev'],
    )


def test_critical_service_check_connect(cursor_factory, dd_run_check, aggregator, bad_instance):
    with cursor_factory(exception=True):
        check = TeradataCheck(CHECK_NAME, {}, [bad_instance])

        with pytest.raises(
            Exception, match=re.compile('Unable to connect to Teradata. (.*) Failed to connect to localhost')
        ):
            dd_run_check(check)

    aggregator.assert_service_check(
        SERVICE_CHECK_CONNECT,
        ServiceCheck.CRITICAL,
        tags=['teradata_server:localhost', 'teradata_port:1025', 'td_env:dev'],
    )
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, count=1)
