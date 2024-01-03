# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_METRICS

pytestmark = [pytest.mark.e2e, pytest.mark.usefixtures("dd_environment")]


def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(name=metric)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
