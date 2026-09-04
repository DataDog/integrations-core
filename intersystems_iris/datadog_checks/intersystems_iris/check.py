# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections import ChainMap
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.metrics_mapping import MetricsMapping
from datadog_checks.base.types import InstanceType

from .config_models import ConfigMixin

# Endpoint labels that collide with reserved Datadog tag keys. The values are still
# preserved as tags (satisfying the requirement to keep this information visible); only
# the tag *key* is renamed so it does not clash with the special meaning Datadog attaches
# to `host` (infra hostname) and `version` (a reserved software-version facet).
RENAME_LABELS_MAP = {
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

    The endpoint-to-submission mapping is declared in `metrics/default.yaml` and loaded
    via the `METRICS_MAP` file-based mechanism. Every label present in the exposition
    (including `id`, `dir`, `namespace`, `jobtype`, `routine`, `state`, `waitstate`, and,
    on interoperability metrics, `production` and `status`) is preserved under its
    original name. The two labels that collide with reserved Datadog tag keys
    (`host`, `version`) are renamed via `RENAME_LABELS_MAP` so their values are still
    submitted as tags without clashing with Datadog's reserved semantics for those keys.

    The standard OpenMetrics V2 health service check (`intersystems_iris.openmetrics.health`) is left
    enabled at its framework default so that a successful scrape reports `OK` and a
    connection/parse failure reports `CRITICAL`, as required.
    """

    __NAMESPACE__ = 'intersystems_iris'
    DEFAULT_METRIC_LIMIT = 0

    METRICS_MAP = (MetricsMapping(Path('metrics/default.yaml')),)

    def get_config_with_defaults(self, config: InstanceType) -> Mapping[str, Any]:
        # Merge per label rather than letting the instance replace the whole mapping, so an
        # instance that renames one label does not silently lose the collision-avoiding renames
        # it did not mention. The copy also keeps the shared module-level map immutable.
        rename_labels = dict(RENAME_LABELS_MAP)
        rename_labels.update(config.get('rename_labels') or {})
        return ChainMap({'rename_labels': rename_labels}, super().get_config_with_defaults(config))
