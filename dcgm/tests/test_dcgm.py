# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.dcgm import DcgmCheck

from .common import METRICS

pytestmark = [pytest.mark.unit]


def test_check(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)
    for metric in METRICS:
        aggregator.assert_metric(name=f"dcgm.{metric}", at_least=0)
