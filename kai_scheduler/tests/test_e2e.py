# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import INSTANCE_STATE_KEY, live_metadata_metrics

pytestmark = [pytest.mark.e2e]


def test_e2e(dd_agent_check, dd_get_state):
    instance = dd_get_state(INSTANCE_STATE_KEY)
    assert instance, f'{INSTANCE_STATE_KEY} was not saved by dd_environment'

    aggregator = dd_agent_check(rate=True)

    metadata_metrics, config_gated = live_metadata_metrics()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics, check_submission_type=True, check_symmetric_inclusion=True, exclude=config_gated
    )

    for option, component in (
        ('scheduler_endpoint', 'scheduler'),
        ('queue_controller_endpoint', 'queue_controller'),
        ('binder_endpoint', 'binder'),
    ):
        aggregator.assert_service_check(
            'kai.openmetrics.health',
            ServiceCheck.OK,
            tags=[f'endpoint:{instance[option]}', f'kai_component:{component}', 'test:e2e'],
        )
