# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common

pytestmark = pytest.mark.e2e


def test_e2e_standalone(dd_agent_check):
    aggregator = dd_agent_check(common.E2E_INSTANCE[0], rate=True)
    common._assert_standalone_metrics(aggregator, ['server_type:master'], count=2)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_slave(dd_agent_check):
    aggregator = dd_agent_check(common.E2E_INSTANCE[1], rate=True)
    common._assert_standalone_metrics(aggregator, ['server_type:slave'], count=2)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_master(dd_agent_check):
    aggregator = dd_agent_check(common.E2E_INSTANCE[2], rate=True)
    common._assert_standalone_metrics(aggregator, ['server_type:master'], count=2)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
