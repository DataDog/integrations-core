# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import time
from typing import Any, Callable

from datadog_checks.base import AgentCheck
from datadog_checks.base.types import InitConfigType, InstanceType

from .client import CatalystCenterClient
from .collectors import (
    collect_application_health,
    collect_assurance_issues,
    collect_client_experience,
    collect_client_health,
    collect_devices,
    collect_interfaces,
    collect_l3_topology,
    collect_network_health,
    collect_sda_fabric,
    collect_security,
    collect_site_health,
    collect_site_topology,
    collect_stacks,
    collect_topology,
)
from .config_models import ConfigMixin
from .errors import CatalystApiError
from .ndm_models import (
    DeviceMetadata,
    InterfaceMetadata,
    batch_payloads,
    create_device_metadata,
    create_interface_metadata,
)

SERVICE_CHECK_CAN_CONNECT = 'can_connect'
NDM_METADATA_EVENT_TYPE = 'network-devices-metadata'


class CiscoCatalystCenterCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'cisco_catalyst_center'

    def __init__(self, name: str, init_config: InitConfigType, instances: list[InstanceType]) -> None:
        super().__init__(name, init_config, instances)
        self._client: CatalystCenterClient | None = None

    @property
    def client(self) -> CatalystCenterClient:
        """The API client, built on first use so that config validation runs first."""
        if self._client is None:
            self._client = CatalystCenterClient(self.instance, http=self.http, log=self.log)
        return self._client

    def _option(self, name: str, default: Any) -> Any:
        value = self.instance.get(name)
        return default if value is None else value

    def _interface_views(self) -> tuple[str, ...]:
        """Which interface views to request.

        ``configuration`` comes first so that later views cannot overwrite the descriptive
        fields. A view replaces the field set rather than extending it, so each one costs its own
        paginated call -- which is why statistics and PoE are separately switchable.
        """
        views = ['configuration']
        if self._option('collect_interface_statistics', True):
            views.append('statistics')
        if self._option('collect_interface_poe', False):
            views.append('poE')
        return tuple(views)

    def _run(self, name: str, collector: Callable[[], Any]) -> bool:
        """Run one collector, containing its failure.

        A single unreachable domain must not cost the whole cycle: losing site health should not
        also lose device health. The service check reflects whether *anything* failed, so a
        partial collection is still visible rather than silently degraded.
        """
        try:
            collector()
        except CatalystApiError as exc:
            # Carries Cisco's x-correlation-id, which is the only reference TAC will act on.
            self.log.error('Catalyst Center %s collection failed: %s', name, exc)
            return False
        except Exception:
            self.log.exception('Unexpected failure collecting Catalyst Center %s', name)
            return False
        return True

    def _send_ndm_metadata(
        self, devices: list[dict[str, Any]], interfaces: dict[str, dict[str, Any]], namespace: str
    ) -> None:
        """Emit device and interface metadata for Network Device Monitoring.

        The namespace is what ties these records to the ones the SNMP check produces for the same
        hardware, so it is logged at debug: a mismatch is invisible in the UI and shows up only as
        devices that never merge.
        """
        collect_timestamp = int(time.time())

        device_metadata: list[DeviceMetadata] = [create_device_metadata(record, namespace) for record in devices]
        interface_metadata: list[InterfaceMetadata] = [
            create_interface_metadata(record, namespace) for record in interfaces.values()
        ]

        self.log.debug(
            'Submitting NDM metadata for %s devices and %s interfaces in namespace %r',
            len(device_metadata),
            len(interface_metadata),
            namespace,
        )

        for items in (device_metadata, interface_metadata):
            for payload in batch_payloads(namespace, items, collect_timestamp):
                self.event_platform_event(payload.model_dump_json(exclude_none=True), NDM_METADATA_EVENT_TYPE)

    def check(self, _: InstanceType) -> None:
        # The instance's `tags` option is a convention every integration honours, so it is
        # folded in ahead of anything this check derives itself.
        base_tags = list(self.instance.get('tags') or [])
        base_tags.append(f'catalyst_center_host:{self.client.base_url}')
        namespace = self._option('namespace', 'default')

        devices: list[dict[str, Any]] = []

        def _devices() -> None:
            nonlocal devices
            devices = collect_devices(
                self,
                self.client,
                collect_wireless=bool(self._option('collect_wireless', False)),
                base_tags=base_tags,
                namespace=namespace,
            )
            self.gauge('device.count', len(devices), tags=base_tags)

        # Devices first: it is the only call that produces the inventory the stack collector
        # needs, and if it fails there is nothing to fan out over anyway.
        healthy = self._run('devices', _devices)

        if devices and self._option('collect_stacks', True):
            healthy &= self._run(
                'stacks', lambda: collect_stacks(self, self.client, devices, base_tags=base_tags, namespace=namespace)
            )

        interfaces: dict[str, dict[str, Any]] = {}

        if self._option('collect_interfaces', True):

            def _interfaces() -> None:
                nonlocal interfaces
                interfaces = collect_interfaces(
                    self,
                    self.client,
                    views=self._interface_views(),
                    base_tags=base_tags,
                    namespace=namespace,
                )

            healthy &= self._run('interfaces', _interfaces)

        sites: list[dict[str, Any]] = []

        if self._option('collect_site_health', True):

            def _sites() -> None:
                nonlocal sites
                sites = collect_site_health(self, self.client, base_tags=base_tags)

            healthy &= self._run('site health', _sites)

        # One call each, no fan-out, so these are not switchable.
        healthy &= self._run('network health', lambda: collect_network_health(self, self.client, base_tags=base_tags))
        healthy &= self._run('client health', lambda: collect_client_health(self, self.client, base_tags=base_tags))

        if self._option('collect_client_experience', True):
            # One POST, aggregated on the appliance, so no per-client series.
            healthy &= self._run(
                'client experience',
                lambda: collect_client_experience(self, self.client, base_tags=base_tags),
            )

        # -- P1 domains, all gated off by default -------------------------------------
        if self._option('collect_topology', False):
            healthy &= self._run('topology', lambda: collect_topology(self, self.client, base_tags=base_tags))
            healthy &= self._run('site topology', lambda: collect_site_topology(self, self.client, base_tags=base_tags))
            for topology_type in self._option('l3_topology_types', ['ospf']):
                healthy &= self._run(
                    f'L3 topology ({topology_type})',
                    lambda t=topology_type: collect_l3_topology(self, self.client, t, base_tags=base_tags),
                )

        if self._option('collect_sda_fabric', False):
            healthy &= self._run(
                'SD-Access fabric',
                lambda: collect_sda_fabric(self, self.client, devices, base_tags=base_tags),
            )

        if self._option('collect_assurance_issues', False):
            healthy &= self._run(
                'assurance issues', lambda: collect_assurance_issues(self, self.client, base_tags=base_tags)
            )

        if self._option('collect_application_health', False):
            if not sites:
                self.log.warning(
                    'collect_application_health needs the site list, which comes from '
                    'collect_site_health; enable it or no application metrics will be collected'
                )
            # Costs one request per site, so it reuses the sites already collected rather than
            # re-listing the hierarchy.
            healthy &= self._run(
                'application health',
                lambda: collect_application_health(self, self.client, sites, base_tags=base_tags),
            )

        if self._option('collect_security', False):
            healthy &= self._run('security', lambda: collect_security(self, self.client, base_tags=base_tags))

        if self._option('send_ndm_metadata', False):
            healthy &= self._run('NDM metadata', lambda: self._send_ndm_metadata(devices, interfaces, namespace))

        if healthy:
            self.service_check(SERVICE_CHECK_CAN_CONNECT, AgentCheck.OK, tags=base_tags)
        else:
            self.service_check(
                SERVICE_CHECK_CAN_CONNECT,
                AgentCheck.CRITICAL,
                tags=base_tags,
                message='One or more Catalyst Center collectors failed; see the Agent log.',
            )
