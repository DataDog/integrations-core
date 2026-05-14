# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck

from .api import PowerFlexAPI
from .config_models import ConfigMixin
from .constants import (
    BWC_SUB_FIELDS,
    DEVICE_RESOURCE_TYPE,
    DEVICE_STATS_BWC_METRICS,
    DEVICE_STATS_SIMPLE_METRICS,
    PROTECTION_DOMAIN_RESOURCE_TYPE,
    PROTECTION_DOMAIN_STATS_BWC_METRICS,
    PROTECTION_DOMAIN_STATS_SIMPLE_METRICS,
    SDC_RESOURCE_TYPE,
    SDC_STATS_BWC_METRICS,
    SDC_STATS_SIMPLE_METRICS,
    SDS_RESOURCE_TYPE,
    SDS_STATS_BWC_METRICS,
    SDS_STATS_SIMPLE_METRICS,
    SEVERITY_TO_ALERT_TYPE,
    STORAGE_POOL_RESOURCE_TYPE,
    STORAGE_POOL_STATS_BWC_METRICS,
    STORAGE_POOL_STATS_SIMPLE_METRICS,
    SYSTEM_MDM_CLUSTER_SIMPLE_METRICS,
    SYSTEM_MDM_CLUSTER_STATE_METRICS,
    SYSTEM_RESOURCE_TYPE,
    SYSTEM_STATS_BWC_METRICS,
    SYSTEM_STATS_SIMPLE_METRICS,
    VOLUME_RESOURCE_TYPE,
    VOLUME_STATS_BWC_METRICS,
    VOLUME_STATS_SIMPLE_METRICS,
)
from .resource_filters import ResourceFilter, parse_resource_filters, should_collect_resource, should_collect_statistics

class DellPowerflexCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'dell_powerflex'

    def __init__(self, name: str, init_config: dict, instances: list) -> None:
        super().__init__(name, init_config, instances)
        self._base_tags: list[str] = []
        self._api: PowerFlexAPI
        self._resource_filters: list[ResourceFilter] = []
        self.check_initializations.append(self._parse_config)

    def _parse_config(self) -> None:
        self._base_tags = [f'powerflex_gateway_url:{self.config.powerflex_gateway_url}'] + list(self.config.tags or ())
        self._api = PowerFlexAPI(
            self.http,
            self.config.powerflex_gateway_url,
            username=self.config.powerflex_username,
            password=self.config.powerflex_password,
            client_id=self.config.powerflex_client_id,  # type: ignore[arg-type]
            logger=self.log,
            min_collection_interval=self.config.min_collection_interval,  # type: ignore[arg-type]
        )
        self._resource_filters = parse_resource_filters(self.config.resource_filters, self.log)

    def check(self, _: Any) -> None:
        try:
            self._api.get_version()
            self.gauge('api.can_connect', 1, tags=self._base_tags)
        except (ConnectionError, HTTPError, InvalidURL, Timeout) as e:
            self.log.warning('Could not connect to PowerFlex Gateway, skipping metric collection: %s', e)
            self.gauge('api.can_connect', 0, tags=self._base_tags)
            return
        self._api._ensure_authenticated()
        for collector in (
            self._collect_systems,
            self._collect_volumes,
            self._collect_storage_pools,
            self._collect_protection_domains,
            self._collect_sds_list,
            self._collect_sdc_list,
            self._collect_devices,
            self._collect_events_and_alerts,
        ):
            try:
                collector()
            except Exception as e:
                self.log.warning('Failed during %s collection: %s', collector.__name__, e)

    def _collect_statistics(
        self,
        work: list[tuple[str, list[str]]],
        stats_api: Callable[[str], dict],
        simple_metrics: list[tuple[str, str]],
        bwc_metrics: list[tuple[str, str]],
    ) -> None:
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_resource = {executor.submit(stats_api, resource_id): (resource_id, tags) for resource_id, tags in work}
            for future in as_completed(future_to_resource):
                resource_id, tags = future_to_resource[future]
                try:
                    stats = future.result()
                except Exception as e:
                    self.log.warning('Failed to collect statistics for %s: %s', resource_id, e)
                    continue
                for api_field, metric_suffix in simple_metrics:
                    self.gauge(metric_suffix, stats.get(api_field), tags=tags)
                self._collect_bwc_metrics(stats, bwc_metrics, tags)

    def _collect_systems(self) -> None:
        systems = self._api.get_systems()
        self.log.debug('Collected %d systems', len(systems))
        stats_work: list[tuple[str, list[str]]] = []
        for system in systems:
            try:
                tags = self._collect_system(system)
                stats_work.append((system.get('id', ''), tags))
            except Exception as e:
                self.log.warning('Failed to collect metrics for system %s: %s', system.get('id'), e)
        if stats_work:
            self._collect_statistics(
                stats_work, self._api.get_system_statistics, SYSTEM_STATS_SIMPLE_METRICS, SYSTEM_STATS_BWC_METRICS
            )

    def _collect_system(self, system: dict) -> list[str]:
        tags = self._base_tags + [f"system_id:{system.get('id', '')}", f"dell_type:{SYSTEM_RESOURCE_TYPE}"]
        if system.get('name'):
            tags = tags + [f"system_name:{system.get('name', '')}"]
        self.gauge('system.count', 1, tags=tags)
        mdm_cluster = system.get('mdmCluster', {})
        for api_field, metric_suffix in SYSTEM_MDM_CLUSTER_SIMPLE_METRICS:
            self.gauge(metric_suffix, mdm_cluster.get(api_field), tags=tags)
        for api_field, metric_suffix, tag_key in SYSTEM_MDM_CLUSTER_STATE_METRICS:
            self.gauge(
                metric_suffix,
                1,
                tags=tags + [f"{tag_key}:{mdm_cluster.get(api_field, '')}"],
            )
        return tags

    def _collect_volumes(self) -> None:
        volumes = self._api.get_volumes()
        self.log.debug('Collected %d volumes', len(volumes))
        collect_stats = should_collect_statistics(VOLUME_RESOURCE_TYPE, self._resource_filters)
        stats_work: list[tuple[str, list[str]]] = []
        for volume in volumes:
            try:
                if not should_collect_resource(VOLUME_RESOURCE_TYPE, volume, self._resource_filters, self.log):
                    continue
                tags = self._collect_volume(volume)
                if collect_stats:
                    stats_work.append((volume.get('id', ''), tags))
            except Exception as e:
                self.log.warning('Failed to collect metrics for volume %s: %s', volume.get('id'), e)
        if stats_work:
            self._collect_statistics(
                stats_work, self._api.get_volume_statistics, VOLUME_STATS_SIMPLE_METRICS, VOLUME_STATS_BWC_METRICS
            )

    def _collect_volume(self, volume: dict) -> list[str]:
        tags = self._base_tags + [
            f"volume_id:{volume.get('id', '')}",
            f"volume_name:{volume.get('name', '')}",
            f"volume_type:{volume.get('volumeType', '')}",
            f"storage_pool_id:{volume.get('storagePoolId', '')}",
            f"dell_type:{VOLUME_RESOURCE_TYPE}",
        ]
        if volume.get('ancestorVolumeId'):
            tags = tags + [f"ancestor_volume_id:{volume.get('ancestorVolumeId', '')}"]
        self.gauge('volume.count', 1, tags=tags)
        for sdc in volume.get('mappedSdcInfo') or []:
            mapping_tags = tags + [f"sdc_id:{sdc.get('sdcId', '')}"]
            self.gauge('volume.sdc_mapping', 1, tags=mapping_tags)
        return tags

    def _collect_storage_pools(self) -> None:
        storage_pools = self._api.get_storage_pools()
        self.log.debug('Collected %d storage pools', len(storage_pools))
        collect_stats = should_collect_statistics(STORAGE_POOL_RESOURCE_TYPE, self._resource_filters)
        stats_work: list[tuple[str, list[str]]] = []
        for pool in storage_pools:
            try:
                if not should_collect_resource(STORAGE_POOL_RESOURCE_TYPE, pool, self._resource_filters, self.log):
                    continue
                tags = self._collect_storage_pool(pool)
                if collect_stats:
                    stats_work.append((pool.get('id', ''), tags))
            except Exception as e:
                self.log.warning('Failed to collect metrics for storage pool %s: %s', pool.get('id'), e)
        if stats_work:
            self._collect_statistics(
                stats_work,
                self._api.get_storage_pool_statistics,
                STORAGE_POOL_STATS_SIMPLE_METRICS,
                STORAGE_POOL_STATS_BWC_METRICS,
            )

    def _collect_storage_pool(self, pool: dict) -> list[str]:
        tags = self._base_tags + [
            f"storage_pool_id:{pool.get('id', '')}",
            f"storage_pool_name:{pool.get('name', '')}",
            f"protection_domain_id:{pool.get('protectionDomainId', '')}",
            f"dell_type:{STORAGE_POOL_RESOURCE_TYPE}",
        ]
        self.gauge('storage_pool.count', 1, tags=tags)
        return tags

    def _collect_protection_domains(self) -> None:
        protection_domains = self._api.get_protection_domains()
        self.log.debug('Collected %d protection domains', len(protection_domains))
        collect_stats = should_collect_statistics(PROTECTION_DOMAIN_RESOURCE_TYPE, self._resource_filters)
        stats_work: list[tuple[str, list[str]]] = []
        for pd in protection_domains:
            try:
                if not should_collect_resource(PROTECTION_DOMAIN_RESOURCE_TYPE, pd, self._resource_filters, self.log):
                    continue
                tags = self._collect_protection_domain(pd)
                if collect_stats:
                    stats_work.append((pd.get('id', ''), tags))
            except Exception as e:
                self.log.warning('Failed to collect metrics for protection domain %s: %s', pd.get('id'), e)
        if stats_work:
            self._collect_statistics(
                stats_work,
                self._api.get_protection_domain_statistics,
                PROTECTION_DOMAIN_STATS_SIMPLE_METRICS,
                PROTECTION_DOMAIN_STATS_BWC_METRICS,
            )

    def _collect_protection_domain(self, pd: dict) -> list[str]:
        tags = self._base_tags + [
            f"protection_domain_id:{pd.get('id', '')}",
            f"protection_domain_name:{pd.get('name', '')}",
            f"system_id:{pd.get('systemId', '')}",
            f"dell_type:{PROTECTION_DOMAIN_RESOURCE_TYPE}",
        ]
        self.gauge('protection_domain.count', 1, tags=tags)
        return tags

    def _collect_sds_list(self) -> None:
        sds_list = self._api.get_sds_list()
        self.log.debug('Collected %d SDSs', len(sds_list))
        collect_stats = should_collect_statistics(SDS_RESOURCE_TYPE, self._resource_filters)
        stats_work: list[tuple[str, list[str]]] = []
        for sds in sds_list:
            try:
                if not should_collect_resource(SDS_RESOURCE_TYPE, sds, self._resource_filters, self.log):
                    continue
                tags = self._collect_sds(sds)
                if collect_stats:
                    stats_work.append((sds.get('id', ''), tags))
            except Exception as e:
                self.log.warning('Failed to collect metrics for SDS %s: %s', sds.get('id'), e)
        if stats_work:
            self._collect_statistics(
                stats_work, self._api.get_sds_statistics, SDS_STATS_SIMPLE_METRICS, SDS_STATS_BWC_METRICS
            )

    def _collect_sds(self, sds: dict) -> list[str]:
        tags = self._base_tags + [
            f"sds_id:{sds.get('id', '')}",
            f"sds_name:{sds.get('name', '')}",
            f"protection_domain_id:{sds.get('protectionDomainId', '')}",
            f"dell_type:{SDS_RESOURCE_TYPE}",
        ]
        if sds.get('faultSetId'):
            tags = tags + [f"fault_set_id:{sds.get('faultSetId', '')}"]
        self.gauge('sds.count', 1, tags=tags)
        return tags

    def _collect_sdc_list(self) -> None:
        sdc_list = self._api.get_sdc_list()
        self.log.debug('Collected %d SDCs', len(sdc_list))
        collect_stats = should_collect_statistics(SDC_RESOURCE_TYPE, self._resource_filters)
        stats_work: list[tuple[str, list[str]]] = []
        for sdc in sdc_list:
            try:
                if not should_collect_resource(SDC_RESOURCE_TYPE, sdc, self._resource_filters, self.log):
                    continue
                tags = self._collect_sdc(sdc)
                if collect_stats:
                    stats_work.append((sdc.get('id', ''), tags))
            except Exception as e:
                self.log.warning('Failed to collect metrics for SDC %s: %s', sdc.get('id'), e)
        if stats_work:
            self._collect_statistics(
                stats_work, self._api.get_sdc_statistics, SDC_STATS_SIMPLE_METRICS, SDC_STATS_BWC_METRICS
            )

    def _collect_sdc(self, sdc: dict) -> list[str]:
        tags = self._base_tags + [
            f"sdc_id:{sdc.get('id', '')}",
            f"sdc_guid:{sdc.get('sdcGuid', '')}",
            f"sdc_type:{sdc.get('sdcType', '')}",
            f"sdc_ip:{sdc.get('sdcIp', '')}",
            f"dell_type:{SDC_RESOURCE_TYPE}",
        ]
        if sdc.get('peerMdmId'):
            tags = tags + [f"peer_mdm_id:{sdc.get('peerMdmId', '')}"]
        self.gauge('sdc.count', 1, tags=tags)
        return tags

    def _collect_devices(self) -> None:
        devices = self._api.get_devices()
        self.log.debug('Collected %d devices', len(devices))
        collect_stats = should_collect_statistics(DEVICE_RESOURCE_TYPE, self._resource_filters)
        stats_work: list[tuple[str, list[str]]] = []
        for device in devices:
            try:
                if not should_collect_resource(DEVICE_RESOURCE_TYPE, device, self._resource_filters, self.log):
                    continue
                tags = self._collect_device(device)
                if collect_stats:
                    stats_work.append((device.get('id', ''), tags))
            except Exception as e:
                self.log.warning('Failed to collect metrics for device %s: %s', device.get('id'), e)
        if stats_work:
            self._collect_statistics(
                stats_work, self._api.get_device_statistics, DEVICE_STATS_SIMPLE_METRICS, DEVICE_STATS_BWC_METRICS
            )

    def _collect_device(self, device: dict) -> list[str]:
        tags = self._base_tags + [
            f"device_id:{device.get('id', '')}",
            f"device_name:{device.get('name', '')}",
            f"current_path_name:{device.get('deviceCurrentPathName', '')}",
            f"storage_pool_id:{device.get('storagePoolId', '')}",
            f"sds_id:{device.get('sdsId', '')}",
            f"dell_type:{DEVICE_RESOURCE_TYPE}",
        ]
        self.gauge('device.count', 1, tags=tags)
        return tags

    def _collect_events_and_alerts(self) -> None:
        now = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if self.config.collect_events:
            last_event_ts = self.read_persistent_cache('last_event_timestamp') or now
            if self._collect_events(last_event_ts):
                self.write_persistent_cache('last_event_timestamp', now)
        if self.config.collect_alerts:
            last_alert_ts = self.read_persistent_cache('last_alert_timestamp') or now
            if self._collect_alerts(last_alert_ts):
                self.write_persistent_cache('last_alert_timestamp', now)

    def _collect_events(self, since: str) -> bool:
        try:
            events = self._api.get_events(since=since)
        except Exception as e:
            self.log.warning('Failed to collect events: %s', e)
            return False
        for event in events:
            self.event(self._build_dd_event(event, 'powerflex_event_name', 'service_name'))
        return True

    def _collect_alerts(self, since: str) -> bool:
        try:
            alerts = self._api.get_alerts(since=since)
        except Exception as e:
            self.log.warning('Failed to collect alerts: %s', e)
            return False
        for alert in alerts:
            self.event(self._build_dd_event(alert, 'powerflex_alert_name', 'service'))
        return True

    def _build_dd_event(self, raw: dict, name_tag_key: str, service_key: str) -> dict:
        raw_ts = raw.get('timestamp')
        timestamp = datetime.fromisoformat(raw_ts).timestamp() if raw_ts else datetime.now(tz=timezone.utc).timestamp()

        severity = raw.get('severity', '')
        alert_type = SEVERITY_TO_ALERT_TYPE.get(severity.upper(), 'info') if severity else 'info'

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
            'alert_type': alert_type,
            'source_type_name': self.__NAMESPACE__,
            'tags': tags,
        }

    def _collect_bwc_metrics(self, stats: dict, bwc_metrics: list[tuple[str, str]], tags: list[str]) -> None:
        for api_field, metric_suffix in bwc_metrics:
            bwc = stats.get(api_field, {})
            for bwc_field, bwc_suffix in BWC_SUB_FIELDS:
                self.gauge(f'{metric_suffix}.{bwc_suffix}', bwc.get(bwc_field), tags=tags)
