# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

# from datadog_checks.base import AgentCheck
from datadog_checks.dcgm import DcgmCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRICS, INSTANCE_WRONG_URL

pytestmark = [pytest.mark.unit]

# TODO In Progress
# https://github.com/DataDog/integrations-core/blob/98e441b4a6d2f88f28f4a63aea0598f997ee1c4e/airflow/tests/test_unit.py#L13-L22
# def test_url():
#     assert CheckEndpoints(INSTANCE["openmetrics_endpoint"])


def test_url(dd_run_check, aggregator):
    check = DcgmCheck('dcgm', {}, [INSTANCE_WRONG_URL])
    check.check(None)
    # dd_run_check(check)


#     aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.CRITICAL)
#     aggregator.assert_metric('dcgm.openmetrics.health', 0, count=1)
#     aggregator.assert_all_metrics_covered()


def test_check(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)
    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(name=f"dcgm.{metric}")
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
