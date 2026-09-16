# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Reports which not-yet-mapped metrics a live GitLab actually exposes.

These metrics are absent from METRICS_MAP and GITALY_METRICS_MAP, so they cannot
be asserted through the check. Scraping the exporters directly answers the only
question that matters before mapping them: does this GitLab emit them at all?

Marked `latest_metrics`, so they are skipped unless explicitly requested:

    ddev env start gitlab exporters
    ddev test gitlab:exporters -- --run-latest-metrics -v -s
"""

import pytest
import requests

from .common import (
    EXPORTERS_ENABLED,
    GITALY_RAW_METRICS_NOT_YET_MAPPED,
    GITLAB_GITALY_PROMETHEUS_ENDPOINT,
    GITLAB_PROMETHEUS_ENDPOINT,
    GITLAB_SIDEKIQ_PROMETHEUS_ENDPOINT,
    GITLAB_WORKHORSE_PROMETHEUS_ENDPOINT,
    SIDEKIQ_RAW_METRICS,
    WORKHORSE_RAW_METRICS,
)

pytestmark = [
    # Registered by datadog_checks_dev and skipped without --run-latest-metrics,
    # which is exactly the opt-in behaviour these checks want.
    pytest.mark.latest_metrics,
    pytest.mark.skipif(not EXPORTERS_ENABLED, reason="requires the `exporters` env"),
]


def scrape(url):
    """Return the set of metric names exposed at a Prometheus endpoint."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return {
        line.split('{')[0].split(' ')[0] for line in response.text.splitlines() if line and not line.startswith('#')
    }


@pytest.mark.parametrize(
    'endpoint, expected',
    [
        pytest.param(GITLAB_GITALY_PROMETHEUS_ENDPOINT, GITALY_RAW_METRICS_NOT_YET_MAPPED, id='gitaly'),
        pytest.param(GITLAB_WORKHORSE_PROMETHEUS_ENDPOINT, WORKHORSE_RAW_METRICS, id='workhorse'),
        pytest.param(GITLAB_SIDEKIQ_PROMETHEUS_ENDPOINT, SIDEKIQ_RAW_METRICS, id='sidekiq'),
        pytest.param(GITLAB_PROMETHEUS_ENDPOINT, ['sidekiq_enqueued_jobs_total'], id='rails'),
    ],
)
def test_exporter_exposes_unmapped_metrics_given_live_gitlab_reports_presence(endpoint, expected):
    exposed = scrape(endpoint)

    # A histogram appears as _bucket/_sum/_count, a counter may drop _total.
    def present(name):
        base = name[:-6] if name.endswith('_total') else name
        return any(
            candidate in exposed for candidate in (name, base, f'{base}_total', f'{base}_bucket', f'{base}_count')
        )

    missing = [name for name in expected if not present(name)]

    print(f'\n{endpoint}  ({len(exposed)} metric names)')
    for name in expected:
        print(f'  {"PRESENT" if present(name) else "absent ":<8} {name}')

    assert not missing, f'not exposed by {endpoint}: {missing}'
