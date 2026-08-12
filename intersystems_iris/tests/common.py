# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

# `metadata.csv` catalogs every metric IRIS can publish on `/api/monitor/metrics`, which is a
# superset of what any single instance emits: some families only appear once the instance takes
# on a role, joins a topology, or has recorded traffic in the current sampling window. Both the
# offline fixture and the integration container are standalone, non-mirrored instances with no
# ECP peers, so those families are legitimately absent and have to be excused before asserting
# that everything else in the catalog was collected.

# ECP and mirror activity metrics, only published once the instance actually participates in a
# distributed cache relationship or a mirror.
_TOPOLOGY_GATED_PREFIXES = (
    'intersystems_iris.ecp.',
    'intersystems_iris.ecps.',
    'intersystems_iris.mirror.',
)

# ...with these exceptions, which report configured capacity or the instance's own role rather
# than peer activity, and so are published even by a standalone instance.
_TOPOLOGY_INDEPENDENT = frozenset(
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
_SAMPLING_GATED = frozenset(
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

# Metrics gated on instance state rather than topology: a database configured with a size cap,
# and SQL queries in flight at the exact moment of the scrape.
_STATE_GATED = frozenset(
    {
        'intersystems_iris.db.file_limit_percent',
        'intersystems_iris.sql.active_queries',
        'intersystems_iris.sql.active_queries_95_percentile',
        'intersystems_iris.sql.active_queries_99_percentile',
    }
)


def unconditional_metadata_metrics(metadata_metrics: dict[str, Any]) -> dict[str, Any]:
    """
    `metadata_metrics` minus the deployment-conditional families above, i.e. exactly what a
    reachable standalone IRIS instance is expected to publish.

    Asserting symmetric inclusion against this subset keeps `metadata.csv` honest -- a declared
    metric with no emitter behind it still fails the build -- while tolerating the families this
    environment cannot produce. If a future test topology starts emitting one of the excused
    families, the corresponding entry should move out of the sets above.
    """
    conditional = _SAMPLING_GATED | _STATE_GATED
    return {
        name: metadata
        for name, metadata in metadata_metrics.items()
        if name not in conditional and (name in _TOPOLOGY_INDEPENDENT or not name.startswith(_TOPOLOGY_GATED_PREFIXES))
    }
