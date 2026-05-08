# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.n8n import N8nCheck

from . import common

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


def _run_check_twice(instance: dict[str, Any], dd_run_check: Callable[[N8nCheck], Any]) -> N8nCheck:
    check = N8nCheck('n8n', {}, [instance])
    # First run primes any one-shot/cached metrics; the second exercises the steady state.
    dd_run_check(check)
    dd_run_check(check)
    return check


@pytest.fixture
def warmed_main(
    instance: dict[str, Any],
    dd_run_check: Callable[[N8nCheck], Any],
    aggregator: AggregatorStub,
) -> N8nCheck:
    return _run_check_twice(instance, dd_run_check)


@pytest.fixture
def warmed_both(
    instance: dict[str, Any],
    worker_instance: dict[str, Any],
    dd_run_check: Callable[[N8nCheck], Any],
    aggregator: AggregatorStub,
) -> AggregatorStub:
    """Run the check against both the main and worker /metrics endpoints into one aggregator."""
    _run_check_twice(instance, dd_run_check)
    _run_check_twice(worker_instance, dd_run_check)
    return aggregator


def test_all_metadata_metrics_emitted(warmed_both: AggregatorStub):
    """Across main and worker, every metadata metric for this n8n version is emitted."""
    common.drop_rare_event_metrics(warmed_both)
    warmed_both.assert_metrics_using_metadata(
        common.get_all_metadata_metrics(exclude_rare=True),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


def test_readiness_check_metric(warmed_main: N8nCheck, aggregator: AggregatorStub):
    aggregator.assert_metric('n8n.readiness.check', value=1, tags=['status_code:200', 'n8n_process:main'], at_least=1)
