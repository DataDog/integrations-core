# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize(
    "instance, custom_tags",
    [
        [common.E2E_INSTANCE[0], ["server_type:master"]],
        [common.E2E_INSTANCE[1], ["server_type:slave"]],
        [common.E2E_INSTANCE[2], ["server_type:master"]],
        [common.E2E_INSTANCE[3], ["server_type:master"]],
        [common.E2E_INSTANCE[4], ["server_type:slave"]],
        [common.E2E_INSTANCE[5], ["server_type:master"]],
    ],
    ids=common.E2E_INSTANCE_IDS,
)
def test_e2e(dd_agent_check, instance, custom_tags):
    aggregator = dd_agent_check(instance, rate=True)
    common._assert_standalone_metrics(aggregator, custom_tags, count=2)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
