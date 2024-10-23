# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from . import common


@pytest.mark.e2e
def test_check_aws_neuron_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric, _ in common.TEST_METRICS.items():
        aggregator.assert_metric(name=metric)

    aggregator.assert_service_check('aws_neuron.openmetrics.health', ServiceCheck.OK)
