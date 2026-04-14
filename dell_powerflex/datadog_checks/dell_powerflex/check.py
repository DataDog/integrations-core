# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck

from .api import PowerFlexAPI
from .config_models import ConfigMixin
from .constants import (
    BWC_SUB_FIELDS,
    PROTECTION_DOMAIN_METRIC_PREFIX,
    PROTECTION_DOMAIN_STATS_BWC_METRICS,
    PROTECTION_DOMAIN_STATS_SIMPLE_METRICS,
    SDC_METRIC_PREFIX,
    SDC_STATS_BWC_METRICS,
    SDC_STATS_SIMPLE_METRICS,
    SDS_METRIC_PREFIX,
    SDS_STATS_BWC_METRICS,
    SDS_STATS_SIMPLE_METRICS,
    STORAGE_POOL_METRIC_PREFIX,
    STORAGE_POOL_STATS_BWC_METRICS,
    STORAGE_POOL_STATS_SIMPLE_METRICS,
    SYSTEM_MDM_CLUSTER_SIMPLE_METRICS,
    SYSTEM_MDM_CLUSTER_STATE_METRICS,
    SYSTEM_METRIC_PREFIX,
    SYSTEM_STATS_BWC_METRICS,
    SYSTEM_STATS_SIMPLE_METRICS,
    VOLUME_METRIC_PREFIX,
    VOLUME_STATS_BWC_METRICS,
    VOLUME_STATS_SIMPLE_METRICS,
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
            self._collect_volumes()
            self._collect_storage_pools()
            self._collect_protection_domains()
            self._collect_sds_list()
            self._collect_sdc_list()
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

    def _collect_volumes(self) -> None:
        for volume in self._api.get_volumes():
            try:
                self._collect_volume(volume)
            except Exception as e:
                self.log.warning('Failed to collect metrics for volume %s: %s', volume.get('id'), e)

    def _collect_volume(self, volume: dict) -> None:
        tags = self._base_tags + [
            f"volume_id:{volume['id']}",
            f"volume_name:{volume['name']}",
            f"volume_type:{volume['volumeType']}",
            f"storage_pool_id:{volume['storagePoolId']}",
        ]
        if volume.get('ancestorVolumeId'):
            tags = tags + [f"ancestor_volume_id:{volume['ancestorVolumeId']}"]
        for sdc in volume.get('mappedSdcInfo') or []:
            tags = tags + [f"sdc_id:{sdc['sdcId']}"]
        self._collect_volume_statistics(volume['id'], tags)

    def _collect_storage_pools(self) -> None:
        for pool in self._api.get_storage_pools():
            try:
                self._collect_storage_pool(pool)
            except Exception as e:
                self.log.warning('Failed to collect metrics for storage pool %s: %s', pool.get('id'), e)

    def _collect_storage_pool(self, pool: dict) -> None:
        tags = self._base_tags + [
            f"storage_pool_id:{pool['id']}",
            f"storage_pool_name:{pool['name']}",
            f"protection_domain_id:{pool['protectionDomainId']}",
        ]
        self._collect_storage_pool_statistics(pool['id'], tags)

    def _collect_storage_pool_statistics(self, pool_id: str, tags: list[str]) -> None:
        stats = self._api.get_storage_pool_statistics(pool_id)
        for api_field, metric_suffix in STORAGE_POOL_STATS_SIMPLE_METRICS:
            self.gauge(f'{STORAGE_POOL_METRIC_PREFIX}.{metric_suffix}', stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, STORAGE_POOL_METRIC_PREFIX, STORAGE_POOL_STATS_BWC_METRICS, tags)

    def _collect_protection_domains(self) -> None:
        for pd in self._api.get_protection_domains():
            try:
                self._collect_protection_domain(pd)
            except Exception as e:
                self.log.warning('Failed to collect metrics for protection domain %s: %s', pd.get('id'), e)

    def _collect_protection_domain(self, pd: dict) -> None:
        tags = self._base_tags + [
            f"protection_domain_id:{pd['id']}",
            f"protection_domain_name:{pd['name']}",
            f"system_id:{pd['systemId']}",
        ]
        self._collect_protection_domain_statistics(pd['id'], tags)

    def _collect_protection_domain_statistics(self, pd_id: str, tags: list[str]) -> None:
        stats = self._api.get_protection_domain_statistics(pd_id)
        for api_field, metric_suffix in PROTECTION_DOMAIN_STATS_SIMPLE_METRICS:
            self.gauge(f'{PROTECTION_DOMAIN_METRIC_PREFIX}.{metric_suffix}', stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, PROTECTION_DOMAIN_METRIC_PREFIX, PROTECTION_DOMAIN_STATS_BWC_METRICS, tags)

    def _collect_sdc_list(self) -> None:
        for sdc in self._api.get_sdc_list():
            try:
                self._collect_sdc(sdc)
            except Exception as e:
                self.log.warning('Failed to collect metrics for SDC %s: %s', sdc.get('id'), e)

    def _collect_sdc(self, sdc: dict) -> None:
        tags = self._base_tags + [
            f"sdc_id:{sdc['id']}",
            f"sdc_guid:{sdc['sdcGuid']}",
            f"sdc_type:{sdc['sdcType']}",
            f"sdc_ip:{sdc['sdcIp']}",
        ]
        if sdc.get('peerMdmId'):
            tags = tags + [f"peer_mdm_id:{sdc['peerMdmId']}"]
        self._collect_sdc_statistics(sdc['id'], tags)

    def _collect_sdc_statistics(self, sdc_id: str, tags: list[str]) -> None:
        stats = self._api.get_sdc_statistics(sdc_id)
        for api_field, metric_suffix in SDC_STATS_SIMPLE_METRICS:
            self.gauge(f'{SDC_METRIC_PREFIX}.{metric_suffix}', stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, SDC_METRIC_PREFIX, SDC_STATS_BWC_METRICS, tags)

    def _collect_sds_list(self) -> None:
        for sds in self._api.get_sds_list():
            try:
                self._collect_sds(sds)
            except Exception as e:
                self.log.warning('Failed to collect metrics for SDS %s: %s', sds.get('id'), e)

    def _collect_sds(self, sds: dict) -> None:
        tags = self._base_tags + [
            f"sds_id:{sds['id']}",
            f"sds_name:{sds['name']}",
            f"protection_domain_id:{sds['protectionDomainId']}",
        ]
        if sds.get('faultSetId'):
            tags = tags + [f"fault_set_id:{sds['faultSetId']}"]
        self._collect_sds_statistics(sds['id'], tags)

    def _collect_sds_statistics(self, sds_id: str, tags: list[str]) -> None:
        stats = self._api.get_sds_statistics(sds_id)
        for api_field, metric_suffix in SDS_STATS_SIMPLE_METRICS:
            self.gauge(f'{SDS_METRIC_PREFIX}.{metric_suffix}', stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, SDS_METRIC_PREFIX, SDS_STATS_BWC_METRICS, tags)

    def _collect_bwc_metrics(
        self, stats: dict, metric_prefix: str, bwc_metrics: list[tuple[str, str]], tags: list[str]
    ) -> None:
        for api_field, metric_suffix in bwc_metrics:
            bwc = stats.get(api_field, {})
            prefix = f'{metric_prefix}.{metric_suffix}'
            for bwc_field, bwc_suffix in BWC_SUB_FIELDS:
                self.gauge(f'{prefix}.{bwc_suffix}', bwc.get(bwc_field), tags=tags)

    def _collect_volume_statistics(self, volume_id: str, tags: list[str]) -> None:
        stats = self._api.get_volume_statistics(volume_id)
        for api_field, metric_suffix in VOLUME_STATS_SIMPLE_METRICS:
            self.gauge(f'{VOLUME_METRIC_PREFIX}.{metric_suffix}', stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, VOLUME_METRIC_PREFIX, VOLUME_STATS_BWC_METRICS, tags)

    def _collect_system_statistics(self, system_id: str, tags: list[str]) -> None:
        stats = self._api.get_system_statistics(system_id)
        for api_field, metric_suffix in SYSTEM_STATS_SIMPLE_METRICS:
            self.gauge(f'{SYSTEM_METRIC_PREFIX}.{metric_suffix}', stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, SYSTEM_METRIC_PREFIX, SYSTEM_STATS_BWC_METRICS, tags)
