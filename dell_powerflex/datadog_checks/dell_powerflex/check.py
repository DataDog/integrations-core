# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timezone
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck

from .api import PowerFlexAPI
from .config_models import ConfigMixin
from .constants import (
    BWC_SUB_FIELDS,
    DEVICE_METRIC_PREFIX,
    DEVICE_STATS_BWC_METRICS,
    DEVICE_STATS_SIMPLE_METRICS,
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
from .resource_filters import parse_resource_filters, should_collect_resource, should_collect_statistics


class DellPowerflexCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'dell_powerflex'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self._base_tags: list[str] = []
        self._api: PowerFlexAPI | None = None
        self._resource_filters: dict = {}
        self.check_initializations.append(self._parse_config)

    def _parse_config(self) -> None:
        self._base_tags = [f'powerflex_gateway_url:{self.config.powerflex_gateway_url}']
        self._api = PowerFlexAPI(
            self.http,
            self.config.powerflex_gateway_url,
            username=self.config.powerflex_username,
            password=self.config.powerflex_password,
            client_id=self.config.powerflex_client_id,
            logger=self.log,
        )
        self._resource_filters = parse_resource_filters(self.config.resource_filters, self.log)

    def check(self, _: Any) -> None:
        try:
            self._api.get_version()
            self.gauge('api.can_connect', 1, tags=self._base_tags)
        except (ConnectionError, HTTPError, InvalidURL, Timeout) as e:
            self.log.warning('Could not connect to PowerFlex Gateway: %s', e)
            self.gauge('api.can_connect', 0, tags=self._base_tags)
            return
        self._collect_systems()
        self._collect_volumes()
        self._collect_storage_pools()
        self._collect_protection_domains()
        self._collect_sds_list()
        self._collect_sdc_list()
        self._collect_devices()
        now = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if self.config.collect_events:
            last_event_ts = self.read_persistent_cache('last_event_timestamp') or now
            if self._collect_events(last_event_ts):
                self.write_persistent_cache('last_event_timestamp', now)
        if self.config.collect_alerts:
            last_alert_ts = self.read_persistent_cache('last_alert_timestamp') or now
            if self._collect_alerts(last_alert_ts):
                self.write_persistent_cache('last_alert_timestamp', now)

    def _collect_systems(self) -> None:
        for system in self._api.get_systems():
            try:
                self._collect_system(system)
            except Exception as e:
                self.log.warning('Failed to collect metrics for system %s: %s', system.get('id'), e)

    def _collect_system(self, system: dict) -> None:
        tags = self._base_tags + [f"system_id:{system['id']}", f"dell_type:{SYSTEM_METRIC_PREFIX}"]
        if system.get('name'):
            tags = tags + [f"system_name:{system['name']}"]
        mdm_cluster = system.get('mdmCluster', {})
        for api_field, metric_suffix in SYSTEM_MDM_CLUSTER_SIMPLE_METRICS:
            self.gauge(metric_suffix, mdm_cluster.get(api_field), tags=tags)
        for api_field, metric_suffix, tag_key in SYSTEM_MDM_CLUSTER_STATE_METRICS:
            self.gauge(
                metric_suffix,
                1,
                tags=tags + [f"{tag_key}:{mdm_cluster.get(api_field)}"],
            )
        self._collect_system_statistics(system['id'], tags)

    def _collect_volumes(self) -> None:
        for volume in self._api.get_volumes():
            try:
                if not should_collect_resource('volume', volume, self._resource_filters, self.log):
                    continue
                self._collect_volume(volume)
            except Exception as e:
                self.log.warning('Failed to collect metrics for volume %s: %s', volume.get('id'), e)

    def _collect_volume(self, volume: dict) -> None:
        tags = self._base_tags + [
            f"volume_id:{volume['id']}",
            f"volume_name:{volume['name']}",
            f"volume_type:{volume['volumeType']}",
            f"storage_pool_id:{volume['storagePoolId']}",
            f"dell_type:{VOLUME_METRIC_PREFIX}",
        ]
        if volume.get('ancestorVolumeId'):
            tags = tags + [f"ancestor_volume_id:{volume['ancestorVolumeId']}"]
        for sdc in volume.get('mappedSdcInfo') or []:
            mapping_tags = tags + [f"sdc_id:{sdc['sdcId']}"]
            self.gauge('volume.sdc_mapping', 1, tags=mapping_tags)
        if should_collect_statistics('volume', self._resource_filters):
            self._collect_volume_statistics(volume['id'], tags)

    def _collect_storage_pools(self) -> None:
        for pool in self._api.get_storage_pools():
            try:
                if not should_collect_resource('storage_pool', pool, self._resource_filters, self.log):
                    continue
                self._collect_storage_pool(pool)
            except Exception as e:
                self.log.warning('Failed to collect metrics for storage pool %s: %s', pool.get('id'), e)

    def _collect_storage_pool(self, pool: dict) -> None:
        tags = self._base_tags + [
            f"storage_pool_id:{pool['id']}",
            f"storage_pool_name:{pool['name']}",
            f"protection_domain_id:{pool['protectionDomainId']}",
            f"dell_type:{STORAGE_POOL_METRIC_PREFIX}",
        ]
        if should_collect_statistics('storage_pool', self._resource_filters):
            self._collect_storage_pool_statistics(pool['id'], tags)

    def _collect_storage_pool_statistics(self, pool_id: str, tags: list[str]) -> None:
        stats = self._api.get_storage_pool_statistics(pool_id)
        for api_field, metric_suffix in STORAGE_POOL_STATS_SIMPLE_METRICS:
            self.gauge(metric_suffix, stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, STORAGE_POOL_STATS_BWC_METRICS, tags)

    def _collect_protection_domains(self) -> None:
        for pd in self._api.get_protection_domains():
            try:
                if not should_collect_resource('protection_domain', pd, self._resource_filters, self.log):
                    continue
                self._collect_protection_domain(pd)
            except Exception as e:
                self.log.warning('Failed to collect metrics for protection domain %s: %s', pd.get('id'), e)

    def _collect_protection_domain(self, pd: dict) -> None:
        tags = self._base_tags + [
            f"protection_domain_id:{pd['id']}",
            f"protection_domain_name:{pd['name']}",
            f"system_id:{pd['systemId']}",
            f"dell_type:{PROTECTION_DOMAIN_METRIC_PREFIX}",
        ]
        if should_collect_statistics('protection_domain', self._resource_filters):
            self._collect_protection_domain_statistics(pd['id'], tags)

    def _collect_protection_domain_statistics(self, pd_id: str, tags: list[str]) -> None:
        stats = self._api.get_protection_domain_statistics(pd_id)
        for api_field, metric_suffix in PROTECTION_DOMAIN_STATS_SIMPLE_METRICS:
            self.gauge(metric_suffix, stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, PROTECTION_DOMAIN_STATS_BWC_METRICS, tags)

    def _collect_sdc_list(self) -> None:
        for sdc in self._api.get_sdc_list():
            try:
                if not should_collect_resource('sdc', sdc, self._resource_filters, self.log):
                    continue
                self._collect_sdc(sdc)
            except Exception as e:
                self.log.warning('Failed to collect metrics for SDC %s: %s', sdc.get('id'), e)

    def _collect_sdc(self, sdc: dict) -> None:
        tags = self._base_tags + [
            f"sdc_id:{sdc['id']}",
            f"sdc_guid:{sdc['sdcGuid']}",
            f"sdc_type:{sdc['sdcType']}",
            f"sdc_ip:{sdc['sdcIp']}",
            f"dell_type:{SDC_METRIC_PREFIX}",
        ]
        if sdc.get('peerMdmId'):
            tags = tags + [f"peer_mdm_id:{sdc['peerMdmId']}"]
        if should_collect_statistics('sdc', self._resource_filters):
            self._collect_sdc_statistics(sdc['id'], tags)

    def _collect_sdc_statistics(self, sdc_id: str, tags: list[str]) -> None:
        stats = self._api.get_sdc_statistics(sdc_id)
        for api_field, metric_suffix in SDC_STATS_SIMPLE_METRICS:
            self.gauge(metric_suffix, stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, SDC_STATS_BWC_METRICS, tags)

    def _collect_sds_list(self) -> None:
        for sds in self._api.get_sds_list():
            try:
                if not should_collect_resource('sds', sds, self._resource_filters, self.log):
                    continue
                self._collect_sds(sds)
            except Exception as e:
                self.log.warning('Failed to collect metrics for SDS %s: %s', sds.get('id'), e)

    def _collect_sds(self, sds: dict) -> None:
        tags = self._base_tags + [
            f"sds_id:{sds['id']}",
            f"sds_name:{sds['name']}",
            f"protection_domain_id:{sds['protectionDomainId']}",
            f"dell_type:{SDS_METRIC_PREFIX}",
        ]
        if sds.get('faultSetId'):
            tags = tags + [f"fault_set_id:{sds['faultSetId']}"]
        if should_collect_statistics('sds', self._resource_filters):
            self._collect_sds_statistics(sds['id'], tags)

    def _collect_sds_statistics(self, sds_id: str, tags: list[str]) -> None:
        stats = self._api.get_sds_statistics(sds_id)
        for api_field, metric_suffix in SDS_STATS_SIMPLE_METRICS:
            self.gauge(metric_suffix, stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, SDS_STATS_BWC_METRICS, tags)

    def _collect_devices(self) -> None:
        for device in self._api.get_devices():
            try:
                if not should_collect_resource('device', device, self._resource_filters, self.log):
                    continue
                self._collect_device(device)
            except Exception as e:
                self.log.warning('Failed to collect metrics for device %s: %s', device.get('id'), e)

    def _collect_device(self, device: dict) -> None:
        tags = self._base_tags + [
            f"device_id:{device['id']}",
            f"device_name:{device['name']}",
            f"current_path_name:{device['deviceCurrentPathName']}",
            f"storage_pool_id:{device['storagePoolId']}",
            f"sds_id:{device['sdsId']}",
            f"dell_type:{DEVICE_METRIC_PREFIX}",
        ]
        if should_collect_statistics('device', self._resource_filters):
            self._collect_device_statistics(device['id'], tags)

    def _collect_device_statistics(self, device_id: str, tags: list[str]) -> None:
        stats = self._api.get_device_statistics(device_id)
        for api_field, metric_suffix in DEVICE_STATS_SIMPLE_METRICS:
            self.gauge(metric_suffix, stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, DEVICE_STATS_BWC_METRICS, tags)

    def _collect_events(self, since: str) -> bool:
        try:
            events = self._api.get_events(since=since)
        except Exception as e:
            self.log.warning('Failed to collect events: %s', e)
            return False
        for event in events:
            self.event(self._build_dd_event(event, 'powerflex_event_name', 'service_name'))
        return True

    def _build_dd_event(self, raw: dict, name_tag_key: str, service_key: str) -> dict:
        raw_ts = raw.get('timestamp')
        timestamp = (
            datetime.fromisoformat(raw_ts.replace('Z', '+00:00')).timestamp()
            if raw_ts
            else datetime.now(tz=timezone.utc).timestamp()
        )

        # TODO: remap Severity to Datadog severity
        # information -> info
        severity = raw.get('severity', '')

        tags = list(self._base_tags)
        tags.append(f"{name_tag_key}:{raw.get('name', '')}")
        tags.append(f"severity:{severity}")
        tags.append(f"category:{raw.get('category', '')}")
        tags.append(f"domain:{raw.get('domain', '')}")
        tags.append(f"dell_type:{raw.get('resource_type', '')}")
        tags.append(f"resource_name:{raw.get('resource_name', '')}")
        tags.append(f"service_name:{raw.get(service_key, '')}")

        name = raw.get('name', '')
        title = name.replace('_', ' ').title()
        resource_name = raw.get('resource_name', '')
        description = raw.get('description', '')
        msg_text = f"{resource_name}: {description}" if resource_name else description

        return {
            'timestamp': timestamp,
            'event_type': self.__NAMESPACE__,
            'msg_title': title,
            'msg_text': msg_text,
            'alert_type': 'error',
            'source_type_name': self.__NAMESPACE__,
            'tags': tags,
        }

    def _collect_alerts(self, since: str) -> bool:
        try:
            alerts = self._api.get_alerts(since=since)
        except Exception as e:
            self.log.warning('Failed to collect alerts: %s', e)
            return False
        for alert in alerts:
            self.event(self._build_dd_event(alert, 'powerflex_alert_name', 'service'))
        return True

    def _collect_bwc_metrics(self, stats: dict, bwc_metrics: list[tuple[str, str]], tags: list[str]) -> None:
        for api_field, metric_suffix in bwc_metrics:
            bwc = stats.get(api_field, {})
            for bwc_field, bwc_suffix in BWC_SUB_FIELDS:
                self.gauge(f'{metric_suffix}.{bwc_suffix}', bwc.get(bwc_field), tags=tags)

    def _collect_volume_statistics(self, volume_id: str, tags: list[str]) -> None:
        stats = self._api.get_volume_statistics(volume_id)
        for api_field, metric_suffix in VOLUME_STATS_SIMPLE_METRICS:
            self.gauge(metric_suffix, stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, VOLUME_STATS_BWC_METRICS, tags)

    def _collect_system_statistics(self, system_id: str, tags: list[str]) -> None:
        stats = self._api.get_system_statistics(system_id)
        for api_field, metric_suffix in SYSTEM_STATS_SIMPLE_METRICS:
            self.gauge(metric_suffix, stats.get(api_field), tags=tags)
        self._collect_bwc_metrics(stats, SYSTEM_STATS_BWC_METRICS, tags)
