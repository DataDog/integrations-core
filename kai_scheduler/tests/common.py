# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.dev.utils import get_metadata_metrics

HERE = get_here()

CHECK_NAME = 'kai_scheduler'
INSTANCE_STATE_KEY = 'kai_scheduler_instance'
KUBECONFIG_STATE_KEY = 'kai_scheduler_kubeconfig'

SCHEDULER_ENDPOINT = 'http://scheduler:8080/metrics'
QUEUE_CONTROLLER_ENDPOINT = 'http://queue-controller:8080/metrics'
BINDER_ENDPOINT = 'http://binder:8080/metrics'

MOCKED_INSTANCE = {
    'scheduler_endpoint': SCHEDULER_ENDPOINT,
    'queue_controller_endpoint': QUEUE_CONTROLLER_ENDPOINT,
    'binder_endpoint': BINDER_ENDPOINT,
    'tags': ['test:tag'],
}

# The fixtures are captured from the e2e environment, which does not configure a UsageDB or leader election and never
# filters scenarios or exhausts a scenario search budget.
CONFIG_GATED_METRIC_PREFIXES = (
    'kai.action.scenarios.filtered',
    'kai.leader_election.master_status',
    'kai.scenario_search.budget_exhausted',
    'kai.usage_query.latency',
)


def get_fixture_path(filename: str) -> str:
    return os.path.join(HERE, 'fixtures', filename)


def live_metadata_metrics() -> tuple[dict, list[str]]:
    """Return the metadata.csv metrics the e2e environment emits, plus the config-gated names to exclude.

    Splitting them allows asserting symmetric inclusion: every other metadata.csv row has to be emitted, and every
    emitted metric has to have a row. `exclude` alone is not enough, because `assert_metrics_using_metadata` only
    applies it to submitted metrics, never to the metadata.csv keys it checks for absence.
    """
    all_metadata = get_metadata_metrics()
    config_gated = [name for name in all_metadata if name.startswith(CONFIG_GATED_METRIC_PREFIXES)]
    return {name: metadata for name, metadata in all_metadata.items() if name not in config_gated}, config_gated
