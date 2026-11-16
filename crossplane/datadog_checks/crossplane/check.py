# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import ChainMap
from pathlib import Path
from typing import TYPE_CHECKING

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.metrics_mapping import MetricsMapping

from .config_models import ConfigMixin

if TYPE_CHECKING:
    from collections.abc import Mapping

    from datadog_checks.base.types import InstanceType

# Endpoint labels renamed for hygiene; see the class docstring.
RENAME_LABELS_MAP = {
    # `rest_client_requests` (core and provider) tags the Kubernetes API server address under
    # `host`, which collides with the reserved Datadog `host` tag used for host-based metric
    # assignment.
    'host': 'rest_client_host',
    # `go_info` (core and provider) tags the Go runtime version under `version`, which collides
    # with the reserved Datadog `version` tag, normally reserved for the monitored service's own
    # version.
    'version': 'go_version',
    # The `workqueue_*` metrics (core and provider) tag the workqueue under the generic `name`
    # label, whose value is always identical to the `controller` label in practice.
    # `leader_election_master_status` (core only) also carries a `name` label, identifying the
    # election lease rather than a workqueue; it is renamed the same way for consistency since
    # OpenMetrics label renames apply check-wide.
    'name': 'workqueue_name',
    # `engine_watches_started` (core only) tags the watched resource kind under the generic `type`
    # label.
    'type': 'watch_type',
}


class CrossplaneCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    """
    Collects Crossplane core and provider controller-runtime telemetry (reconciliation totals and
    errors, workqueue depth and active workers, circuit breaker activity, managed resource
    readiness/sync/time-to-readiness, and, for Upjet-based providers, external cloud API call and
    Terraform CLI metrics) by scraping a Crossplane core or provider pod's Prometheus metrics
    endpoint.

    The endpoint-to-submission mappings are declared in `metrics/core.yaml` and
    `metrics/provider.yaml` and loaded unconditionally via the `METRICS_MAP` file-based mechanism,
    since either mapping may apply depending on whether the configured endpoint belongs to
    Crossplane core or to a provider.
    """

    __NAMESPACE__ = 'crossplane'
    DEFAULT_METRIC_LIMIT = 0

    METRICS_MAP = (
        MetricsMapping(Path('metrics/core.yaml')),
        MetricsMapping(Path('metrics/provider.yaml')),
    )

    def get_default_config(self) -> dict:
        # A fresh copy each call, since the framework may mutate what this returns. The base check
        # merges this entry by entry with any instance-level `rename_labels`, so an instance that
        # renames one label keeps the collision-avoiding renames it did not mention.
        return {'rename_labels': dict(RENAME_LABELS_MAP)}

    def get_config_with_defaults(self, config: InstanceType) -> Mapping:
        # Preserve file-based metric mappings (METRICS_MAP) and other defaults, then force
        # enable_health_service_check to False so the deprecated OpenMetrics health service check
        # cannot be enabled or emitted, regardless of instance configuration.
        merged = super().get_config_with_defaults(config)
        return ChainMap({'enable_health_service_check': False}, merged)
