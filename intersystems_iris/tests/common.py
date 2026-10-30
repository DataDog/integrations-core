# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Any

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics

FIXTURE_PATH = str(Path(__file__).parent / 'fixtures' / 'metrics.txt')

# `metadata.csv` catalogs every metric IRIS can publish on `/api/monitor/metrics`, which is a
# superset of what any single instance emits: some families only appear once the instance takes
# on a role, joins a topology, or has recorded traffic in the current sampling window. Both the
# offline fixture and the integration container are standalone, non-mirrored instances with no
# ECP peers, so those families are legitimately absent and have to be excused before asserting
# that everything else in the catalog was collected.

# ECP and mirror activity metrics, only published once the instance actually participates in a
# distributed cache relationship or a mirror.
TOPOLOGY_GATED_PREFIXES = (
    'intersystems_iris.ecp.',
    'intersystems_iris.ecps.',
    'intersystems_iris.mirror.',
)

# ...with these exceptions, which report configured capacity or the instance's own role rather
# than peer activity, and so are published even by a standalone instance.
TOPOLOGY_INDEPENDENT = frozenset(
    {
        'intersystems_iris.ecp.conn',
        'intersystems_iris.ecp.conn_max',
        'intersystems_iris.ecps.conn',
        'intersystems_iris.ecps.conn_max',
        'intersystems_iris.mirror.member_type',
    }
)

# Interoperability SAM statistic sensors. Unlike the always-on interface family
# (`interop.hosts`, `interop.messages.*`, ...) these are aggregated over a sampling window and
# only published once matching traffic has been recorded, so the short-lived demo production
# does not reliably surface them. The `http.*` subset additionally needs outbound HTTP adapter
# traffic, which the demo production does not generate at all.
SAMPLING_GATED = frozenset(
    {
        'intersystems_iris.interop.avg_processing_time',
        'intersystems_iris.interop.avg_queueing_time',
        'intersystems_iris.interop.header_count_older_than',
        'intersystems_iris.interop.http.avg_received_chars',
        'intersystems_iris.interop.http.avg_sent_chars',
        'intersystems_iris.interop.http.avg_ttfc',
        'intersystems_iris.interop.http.avg_ttlc',
        'intersystems_iris.interop.http.sample_count',
        'intersystems_iris.interop.http.sample_count_per_sec',
        'intersystems_iris.interop.namespace_storage_mb',
        'intersystems_iris.interop.oldest_message_header_count',
        'intersystems_iris.interop.oldest_message_header_days',
        'intersystems_iris.interop.sample_count',
        'intersystems_iris.interop.sample_count_per_sec',
        'intersystems_iris.interop.session_count',
        'intersystems_iris.interop.session_storage_kb',
    }
)

# Work Queue Manager metrics, published only once the instance has actually dispatched work
# through the WQM. An instance that has been idle since startup does not surface the family at
# all: it is absent from two of the captures taken from live instances, and a container that
# came up idle failed the symmetric assertion on a commit where a second, otherwise identical
# job passed.
ACTIVITY_GATED_PREFIXES = ('intersystems_iris.wqm.',)

# Metrics gated on instance state rather than topology: a database configured with a size cap,
# and SQL queries in flight at the exact moment of the scrape.
STATE_GATED = frozenset(
    {
        'intersystems_iris.db.file_limit_percent',
        'intersystems_iris.sql.active_queries',
        'intersystems_iris.sql.active_queries_95_percentile',
        'intersystems_iris.sql.active_queries_99_percentile',
    }
)


def _partition_metadata_metrics(
    metadata_metrics: dict[str, Any], emitted_prefixes: tuple[str, ...] = ()
) -> tuple[dict[str, Any], list[str]]:
    """
    Split the catalog into the metrics this environment is expected to publish and the ones it
    excuses, i.e. exactly what a reachable standalone IRIS instance emits versus the
    deployment-conditional families above.

    Asserting symmetric inclusion against the first half keeps `metadata.csv` honest -- a declared
    metric with no emitter behind it still fails the build -- while tolerating the families this
    environment cannot produce. If a future test topology starts emitting one of the excused
    families, the corresponding entry should move out of the sets above.

    `emitted_prefixes` re-admits gated families the caller's environment does produce: the
    offline fixture was captured from a busy ECP data server with a live client, so the unit test
    asserts the full `intersystems_iris.ecps.*` and `intersystems_iris.wqm.*` families, while the
    container-backed integration and E2E tests -- standalone instances with no ECP peers, which
    may or may not have driven the work queue by the time they are scraped -- do not.

    Both halves are returned together because they are complements of one another: the caller
    passes the first as the expected mapping and the second as `exclude=`, and deriving them from
    a single filter is what guarantees they cannot drift apart.
    """
    conditional = SAMPLING_GATED | STATE_GATED
    gated_prefixes = TOPOLOGY_GATED_PREFIXES + ACTIVITY_GATED_PREFIXES
    # Re-admission is an exact string match against the tables above, so a prefix that is not one
    # of them -- a missing trailing dot, a renamed constant -- would silently re-excuse the whole
    # family and leave the caller asserting strictly less while still passing. Fail loudly instead.
    if unknown := set(emitted_prefixes) - set(gated_prefixes):
        raise ValueError(f"emitted_prefixes contains prefixes that are not gated: {sorted(unknown)}")
    gated = tuple(prefix for prefix in gated_prefixes if prefix not in emitted_prefixes)
    expected = {
        name: metadata
        for name, metadata in metadata_metrics.items()
        if name not in conditional and (name in TOPOLOGY_INDEPENDENT or not name.startswith(gated))
    }
    excused = [name for name in metadata_metrics if name not in expected]
    return expected, excused


def _assert_metrics_match_metadata(aggregator: AggregatorStub, emitted_prefixes: tuple[str, ...] = ()) -> None:
    """
    Assert the two halves of the metadata.csv contract for a completed scrape.

    Nothing may be submitted that the catalog does not declare, and -- excusing the families
    this environment cannot produce -- everything it declares must have been collected. Both
    tiers of test assert the same contract and differ only in which gated families their
    environment emits, so `emitted_prefixes` is the single knob between them.
    """
    metadata_metrics = get_metadata_metrics()
    expected, excused = _partition_metadata_metrics(metadata_metrics, emitted_prefixes)

    # Nothing may be submitted that metadata.csv does not declare, and the declared types must
    # match what the check submits.
    aggregator.assert_metrics_using_metadata(metadata_metrics, check_submission_type=True)

    # Conversely, every metric the catalog declares for this environment must have been
    # collected -- this is what catches a metadata.csv entry with no emitter behind it.
    # Excusing a family is only half the job: an activity-gated metric that *does* show up would
    # otherwise be reported as submitted but undeclared, since the assertion checks submissions
    # against the trimmed mapping it was handed rather than against metadata.csv itself.
    aggregator.assert_metrics_using_metadata(
        expected,
        exclude=excused,
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


def assert_healthy_scrape(aggregator: AggregatorStub, emitted_prefixes: tuple[str, ...] = ()) -> None:
    """
    Assert that a scrape completed cleanly: the metadata.csv contract holds and the endpoint
    reported healthy.

    All three test tiers make exactly this pair of assertions, so they share one entry point
    rather than each repeating the service check name.
    """
    _assert_metrics_match_metadata(aggregator, emitted_prefixes)
    aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.OK)
