# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin

# Labels exposed by the endpoint that collide with reserved Datadog tag keys. The
# underlying values are still preserved as tags (satisfying the product requirement to
# keep this information visible); only the tag *key* is renamed so it does not clash
# with the special meaning Datadog attaches to `host` (infra hostname) and `version`
# (a reserved facet used for software version tracking).
RENAME_LABELS = {
    # Business-host name on `iris_interop_*` metrics, not the reporting infra host.
    'host': 'interop_host',
    # IRIS product version reported by `iris_system_info`, not the Agent/integration version.
    'version': 'iris_version',
}


class IrisCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    """
    Collects InterSystems IRIS instance telemetry (CPU, cache efficiency, licensing,
    journaling, write daemon, work queue manager, SQL activity, databases/disk, shared
    memory, locks, ECP, the Web Gateway/CSP, mirroring, system status, and, when a
    production is running, interoperability metrics) by scraping the built-in
    `/api/monitor/metrics` OpenMetrics endpoint.

    A single endpoint mapping (`metrics.yaml`) is discovered by convention. Every label
    present in the exposition (including `id`, `dir`, `namespace`, `jobtype`, `routine`,
    `state`, `waitstate`, and, on interoperability metrics, `production` and `status`) is
    preserved under its original name. The two labels that collide with reserved Datadog
    tag keys (`host`, `version`) are renamed via `RENAME_LABELS` so their values are still
    submitted as tags without clashing with Datadog's reserved semantics for those keys.

    The standard OpenMetrics V2 health service check (`iris.openmetrics.health`) is left
    enabled at its framework default so that a successful scrape reports `OK` and a
    connection/parse failure reports `CRITICAL`, as required.
    """

    __NAMESPACE__ = 'iris'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self) -> dict:
        return {
            'rename_labels': dict(RENAME_LABELS),
        }
