# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck

from .api import PowerFlexAPI
from .config_models import ConfigMixin
from .constants import (
    SYSTEM_MDM_CLUSTER_SIMPLE_METRICS,
    SYSTEM_MDM_CLUSTER_STATE_METRICS,
    SYSTEM_METRIC_PREFIX,
    SYSTEM_STATS_BWC_METRICS,
    SYSTEM_STATS_SIMPLE_METRICS,
)


class DellPowerflexCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'dell_powerflex'

    def __init__(self, name, init_config, instances):
        super(DellPowerflexCheck, self).__init__(name, init_config, instances)
        self._base_tags: list[str] = []
        self._api: PowerFlexAPI | None = None
        self.check_initializations.append(self._parse_config)

    def _parse_config(self) -> None:
        self._base_tags = [f'powerflex_gateway_url:{self.config.powerflex_gateway_url}']
        self._api = PowerFlexAPI(self.http, self.config.powerflex_gateway_url)

    def check(self, _: Any) -> None:
        try:
            self._collect_systems()
            self.gauge('api.can_connect', 1, tags=self._base_tags)
        except (ConnectionError, HTTPError, InvalidURL, Timeout) as e:
            self.log.warning('Could not connect to PowerFlex Gateway: %s', e)
            self.gauge('api.can_connect', 0, tags=self._base_tags)

    def _collect_systems(self) -> None:
        for system in self._api.get_systems():
            try:
                self._collect_system(system)
            except Exception as e:
                self.log.warning('Failed to collect metrics for system %s: %s', system.get('id'), e)

    def _collect_system(self, system: dict) -> None:
        tags = self._base_tags + [f"system_id:{system['id']}"]
        if system.get('name'):
            tags = tags + [f"system_name:{system['name']}"]
        mdm_cluster = system.get('mdmCluster', {})
        for api_field, metric_suffix in SYSTEM_MDM_CLUSTER_SIMPLE_METRICS:
            self.gauge(f'{SYSTEM_METRIC_PREFIX}.{metric_suffix}', mdm_cluster.get(api_field), tags=tags)
        for api_field, metric_suffix, tag_key in SYSTEM_MDM_CLUSTER_STATE_METRICS:
            self.gauge(
                f'{SYSTEM_METRIC_PREFIX}.{metric_suffix}',
                1,
                tags=tags + [f"{tag_key}:{mdm_cluster.get(api_field)}"],
            )
        self._collect_system_statistics(system['id'], tags)

    def _collect_system_statistics(self, system_id: str, tags: list[str]) -> None:
        stats = self._api.get_system_statistics(system_id)
        for api_field, metric_suffix in SYSTEM_STATS_SIMPLE_METRICS:
            self.gauge(f'{SYSTEM_METRIC_PREFIX}.{metric_suffix}', stats.get(api_field), tags=tags)
        for api_field, metric_suffix in SYSTEM_STATS_BWC_METRICS:
            bwc = stats.get(api_field, {})
            prefix = f'{SYSTEM_METRIC_PREFIX}.{metric_suffix}'
            self.gauge(f'{prefix}.num_seconds', bwc.get('numSeconds'), tags=tags)
            self.gauge(f'{prefix}.total_weight_in_kb', bwc.get('totalWeightInKb'), tags=tags)
            self.gauge(f'{prefix}.num_occured', bwc.get('numOccured'), tags=tags)
