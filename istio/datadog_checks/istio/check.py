# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .constants import ISTIOD_NAMESPACE
from .metrics import (
    ISTIOD_METRICS,
    ISTIOD_VERSION,
    MESH_METRICS,
    WAYPOINT_METRICS,
    ZTUNNEL_METRICS,
    construct_metrics_config,
)


class IstioCheckV2(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(IstioCheckV2, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        self.scraper_configs = []
        istio_mode = self.instance.get("istio_mode", "sidecar")
        istiod_endpoint = self.instance.get("istiod_endpoint")
        istiod_namespace = self.instance.get("namespace", ISTIOD_NAMESPACE)

        if istio_mode == "ambient":
            self._parse_ambient_config(istiod_endpoint, istiod_namespace)
        elif istio_mode == "sidecar":
            self._parse_sidecar_config(istiod_endpoint, istiod_namespace)
        else:
            raise ConfigurationError(f"Invalid istio_mode '{istio_mode}'. Must be either 'sidecar' or 'ambient'.")

    def _parse_sidecar_config(self, istiod_endpoint, istiod_namespace):
        """Parse configuration for sidecar mode (traditional Istio deployment)."""
        mesh_endpoint = self.instance.get("istio_mesh_endpoint")
        mesh_namespace = istiod_namespace + ".mesh"

        if not mesh_endpoint and not istiod_endpoint:
            raise ConfigurationError(
                "Must specify at least one of the following endpoints: `istio_mesh_endpoint` or `istiod_endpoint`."
            )

        if mesh_endpoint:
            self.scraper_configs.append(self._generate_config(mesh_endpoint, MESH_METRICS, mesh_namespace))
        if istiod_endpoint:
            self.scraper_configs.append(self._generate_config(istiod_endpoint, ISTIOD_METRICS, istiod_namespace))

    def _parse_ambient_config(self, istiod_endpoint, istiod_namespace):
        """Parse configuration for ambient mode (sidecar-less Istio deployment)."""
        ztunnel_endpoint = self.instance.get("ztunnel_endpoint")
        waypoint_endpoint = self.instance.get("waypoint_endpoint")

        if not ztunnel_endpoint and not waypoint_endpoint and not istiod_endpoint:
            raise ConfigurationError(
                "In ambient mode, must specify at least one of: "
                "`ztunnel_endpoint`, `waypoint_endpoint`, or `istiod_endpoint`."
            )

        # Ztunnel provides L4 TCP metrics for ambient mesh
        ztunnel_namespace = istiod_namespace + ".ztunnel"
        if ztunnel_endpoint:
            self.scraper_configs.append(self._generate_config(ztunnel_endpoint, ZTUNNEL_METRICS, ztunnel_namespace))

        # Waypoint provides L7 HTTP/gRPC metrics (optional in ambient mode)
        waypoint_namespace = istiod_namespace + ".waypoint"
        if waypoint_endpoint:
            self.scraper_configs.append(self._generate_config(waypoint_endpoint, WAYPOINT_METRICS, waypoint_namespace))

        # Control plane metrics are the same for both modes
        if istiod_endpoint:
            self.scraper_configs.append(self._generate_config(istiod_endpoint, ISTIOD_METRICS, istiod_namespace))

    def _generate_config(self, endpoint, metrics, namespace):
        metrics = construct_metrics_config(metrics)
        metrics.append(ISTIOD_VERSION)
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
            'namespace': namespace,
        }
        config.update(self.instance)
        # Restore per-scraper namespace so custom ztunnel/waypoint/mesh namespaces are not overwritten by instance
        config['namespace'] = namespace
        return config

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config):
        return ChainMap(config, {'metrics': config.pop('metrics'), 'namespace': config.pop('namespace')})
