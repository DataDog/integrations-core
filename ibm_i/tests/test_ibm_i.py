# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import mock

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.ibm_i import IbmICheck
from datadog_checks.ibm_i.check import SystemInfo


def test_check(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = IbmICheck('ibm_i', {}, [instance])
    check.check(instance)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_fetch_system_info(aggregator, instance):
    check = IbmICheck('ibm_i', {}, [instance])
    check.log = mock.MagicMock()
    with mock.patch('datadog_checks.ibm_i.IbmICheck.execute_query', return_value=[("hostname", "7", "3")]), mock.patch(
        'datadog_checks.ibm_i.IbmICheck._delete_connection'
    ) as delete_conn:
        system_info = check.fetch_system_info()

    assert system_info == SystemInfo(hostname="hostname", os_version=7, os_release=3)
    delete_conn.assert_not_called()
    check.log.assert_not_called()


def test_failed_fetch_system_info(aggregator, instance):
    pass


def test_query_error(aggregator, instance):
    pass
