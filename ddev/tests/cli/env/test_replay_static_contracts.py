# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Static integration contract checks reported with replay validation.

These checks do not need a replay cache. They run from the same configured
context as replay validation so the combined report can show repository-only
asset/metadata issues next to replay-backed behavior and coverage signals.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.cli.env.test_replay_pbt import (
    ReplayPBTContext,
    _asset_metric_metadata_findings,
    _handle_findings,
    _load_asset_queries,
    _load_metadata_rows,
    _skip_unselected,
    replay_pbt_context,  # noqa: F401 - registers the shared fixture
)


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['asset-query-metrics-in-metadata']))
def test_asset_query_metrics_match_metadata(replay_pbt_context: ReplayPBTContext, validation: str):
    """Validate asset query metrics against metadata.csv without replay."""
    property_name = 'asset-query-metrics-in-metadata'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'asset-query-metrics-in-metadata'

    metadata_rows = _load_metadata_rows(replay_pbt_context.repo, replay_pbt_context.integration)
    asset_queries = _load_asset_queries(replay_pbt_context.repo, replay_pbt_context.integration)
    if not asset_queries:
        pytest.skip('Integration has no dashboard or monitor metric queries to validate against metadata.csv.')

    findings = _asset_metric_metadata_findings(
        repo_root=replay_pbt_context.repo,
        integration=replay_pbt_context.integration,
        metadata_rows=metadata_rows,
    )
    _handle_findings(replay_pbt_context, property_name, findings)
