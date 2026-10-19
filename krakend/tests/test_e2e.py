# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable, get_docker_hostname
from datadog_checks.krakend import KrakendCheck
from tests.helpers import get_metrics_from_metadata
from tests.types import InstanceBuilder


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance: InstanceBuilder):
    config = {"init_config": {}, "instances": [instance(True, True, get_docker_hostname(), 9090)]}

    aggregator = dd_agent_check(config, check_rate=True)

    metadata_metrics = get_metrics_from_metadata()

    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


@pytest.mark.e2e
@pytest.mark.parametrize('process', [False, True], ids=['container', 'process'])
def test_e2e_discovery(dd_agent_check_discovery, is_lab, process):
    # In the lab environment we currently do not mount auto_conf.yaml into the
    # Agent container, so the Agent has no Autodiscovery template to trigger
    # config discovery.
    if is_lab:
        pytest.skip('lab does not currently support configuration discovery')

    aggregator = dd_agent_check_discovery(check_rate=True, process=process)

    metadata_metrics = get_metrics_from_metadata()

    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, KrakendCheck)
