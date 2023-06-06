# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import METRICS

pytestmark = [pytest.mark.e2e, pytest.mark.usefixtures("dd_environment")]

# TODO metrics are filing because we need to add count to those predicted ones (nvml.nband, pcie_replay, etc)
# instead of what I'm doing, I should just add them to the common.py file?


def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in METRICS:
        aggregator.assert_metric(name=f"dcgm.{metric}", at_least=0)


# def test_e2e_service_checks(dd_agent_check, instance):
#     aggregator = dd_agent_check(instance, rate=True),
#     aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)
