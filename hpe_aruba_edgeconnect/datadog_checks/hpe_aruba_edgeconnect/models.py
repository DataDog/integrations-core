# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import ipaddress
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .constants import NDM_DEVICE_RESOURCE_TAG, NDM_DEVICE_USER_TAGS_RESOURCE_TAG

log = logging.getLogger(__name__)


@dataclass(init=False, slots=True)
class Appliance:
    """Represents an appliance record returned by the orchestrator API."""

    # TODO remove the ones that are not used (commented out below)
    # id: str
    # uuid: str
    # ne_pk: str
    # appliance_id: int
    host_name: str
    ip: str
    serial: str
    model: str
    # platform: str
    mode: str
    software_version: str
    # hardware_revision: str
    # system_bandwidth: int
    state: int
    site: str | None
    startup_time: int | None
    # network_role: str
    # group_id: str
    # bypass: bool
    # has_unsaved_changes: bool
    # reboot_required: bool
    # web_protocol: str
    # web_protocol_type: int
    # dynamic_uuid: str
    # portal_object_id: str
    # discovered_from: int
    # reachability_channel: int
    # preconfig_status: str | None
    # suricata_version: str
    # signature_family: str
    username: str
    password: str

    def __init__(self, data: dict[str, Any]) -> None:
        # self.id = data.get('id', '')
        # self.uuid = data.get('uuid', '')
        # self.ne_pk = data.get('nePk', '')
        # self.appliance_id = data.get('applianceId', 0)
        self.host_name = data.get('hostName', '')
        self.ip = data.get('ip', '')
        self.serial = data.get('serial', '')
        self.model = data.get('model', '')
        # self.platform = data.get('platform', '')
        self.mode = data.get('mode', '')
        self.software_version = data.get('softwareVersion', '')
        # self.hardware_revision = data.get('hardwareRevision', '')
        # self.system_bandwidth = data.get('systemBandwidth', 0)
        self.state = data.get('state', 0)
        self.site = data.get('site')
        self.startup_time = data.get('startupTime')
        # self.network_role = data.get('networkRole', '')
        # self.group_id = data.get('groupId', '')
        # self.bypass = data.get('bypass', False)
        # self.has_unsaved_changes = data.get('hasUnsavedChanges', False)
        # self.reboot_required = data.get('rebootRequired', False)
        # self.web_protocol = data.get('webProtocol', '')
        # self.web_protocol_type = data.get('webProtocolType', 0)
        # self.dynamic_uuid = data.get('dynamicUuid', '')
        # self.portal_object_id = data.get('portalObjectId', '')
        # self.discovered_from = data.get('discoveredFrom', 0)
        # self.reachability_channel = data.get('reachabilityChannel', 0)
        # self.preconfig_status = data.get('preconfigStatus')
        # self.suricata_version = data.get('suricataVersion', '')
        # self.signature_family = data.get('signatureFamily', '')
        self.username = ''
        self.password = ''

    @property
    def is_reachable(self) -> bool:
        # Appliance state to Orchestrator value mapping:
        # 0 - Unknown ( When an appliance is added to Orchestrator, it
        #   is in this state )
        # 1 - Normal ( Appliance is reachable from Orchestrator)
        # 2 - Unreachable ( Appliance is unreachable from Orchestrator )
        # 3 - Unsupported Version ( Orchestrator does not support this
        #   version of the appliance )
        # 4 - Out of Synchronization ( Orchestrator's cache of appliance
        #   configuration/state is out of sync with the
        #   configuration/state on the appliance )
        # 5 - Synchronization in Progress ( Orchestrator is currently
        #   synchronizing appliances's configuration and state )
        return self.state == 1

    def device_id(self, namespace: str) -> str:
        return f'{namespace}:{self.ip}'

    def tags(self, namespace: str) -> list[str]:
        site = self.site or 'unknown'
        did = self.device_id(namespace)
        return [
            f'device_namespace:{namespace}',
            f'device_ip:{self.ip}',
            f'device_model:{self.model or "unknown"}',
            f'device_hostname:{self.host_name or "unknown"}',
            f'softwareVersion:{self.software_version or "unknown"}',
            'device_vendor:aruba',
            f'site_id:{site}',
            f'site_name:{site}',
            f'{NDM_DEVICE_RESOURCE_TAG}:{did}',
            f'{NDM_DEVICE_USER_TAGS_RESOURCE_TAG}:{did}',
        ]


class Appliances:
    """Collection of appliances with filtering and credential resolution."""

    def __init__(self, raw: list[Appliance]) -> None:
        self._appliances = list(raw)

    def __iter__(self) -> Iterator[Appliance]:
        return iter(self._appliances)

    def __len__(self) -> int:
        return len(self._appliances)

    def filter(self, ip_filter: dict[str, Any] | None) -> None:
        if not ip_filter:
            return
        include = ip_filter.get('include')
        if include:
            self._appliances = [a for a in self._appliances if _ip_matches_any(a.ip, include)]
        exclude = ip_filter.get('exclude')
        if exclude:
            self._appliances = [a for a in self._appliances if not _ip_matches_any(a.ip, exclude)]

    def resolve_credentials(
        self,
        default_username: str,
        default_password: str,
        overrides: list[dict[str, Any]] | None = None,
    ) -> None:
        for appliance in self._appliances:
            appliance.username = default_username
            appliance.password = default_password
            for cred in overrides or []:
                cidr = cred.get('cidr')
                if not cidr:
                    continue
                try:
                    if ipaddress.ip_address(appliance.ip) in ipaddress.ip_network(cidr, strict=False):
                        username = cred.get('username')
                        password = cred.get('password')
                        if username and password:
                            appliance.username = username
                            appliance.password = password
                            log.debug(
                                "Using CIDR-matched credentials for appliance %s (matched %s)",
                                appliance.ip,
                                cidr,
                            )
                        break
                except ValueError:
                    continue
            else:
                log.debug("Using shared credentials for appliance %s", appliance.ip)


def _ip_matches_any(ip: str, patterns: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for pattern in patterns:
        try:
            if '/' in pattern:
                if addr in ipaddress.ip_network(pattern, strict=False):
                    return True
            elif addr == ipaddress.ip_address(pattern):
                return True
        except ValueError:
            continue
    return False
