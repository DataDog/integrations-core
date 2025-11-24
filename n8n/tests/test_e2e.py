# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.docker import get_docker_hostname
from datadog_checks.dev.utils import assert_service_checks
from tests.helpers import get_metrics_from_metadata
from tests.types import InstanceBuilder


@pytest.mark.e2e
def test_check_n8n_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_service_check('n8n.openmetrics.health', ServiceCheck.OK, count=2)
    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance: InstanceBuilder):
    config = {"init_config": {}, "instances": [instance(True, True, get_docker_hostname(), 5678)]}

    aggregator = dd_agent_check(config, check_rate=True)

    metadata_metrics = get_metrics_from_metadata()

    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=False,
    )
