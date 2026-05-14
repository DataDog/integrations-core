# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import ipaddress
import logging
from collections.abc import Iterator
from typing import Any, NotRequired, TypedDict

from .constants import NDM_DEVICE_RESOURCE_TAG, NDM_DEVICE_USER_TAGS_RESOURCE_TAG

log = logging.getLogger(__name__)


class IpFilter(TypedDict):
    include: NotRequired[list[str] | None]
    exclude: NotRequired[list[str] | None]


class ApplianceCredentialOverride(TypedDict):
    cidr: str
    username: str
    password: str


class Appliance:
    __slots__ = (
        'host_name',
        'ip',
        'serial',
        'model',
        'mode',
        'software_version',
        'state',
        'site',
        'username',
        'password',
    )

    def __init__(self, data: dict[str, Any]) -> None:
        self.host_name: str = data.get('hostName', '')
        self.ip: str = data.get('ip', '')
        self.serial: str = data.get('serial', '')
        self.model: str = data.get('model', '')
        self.mode: str = data.get('mode', '')
        self.software_version: str = data.get('softwareVersion', '')
        self.state: int = data.get('state', 0)
        self.site: str | None = data.get('site')
        self.username: str = ''
        self.password: str = ''

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
            f'software_version:{self.software_version or "unknown"}',
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

    def filter(self, ip_filter: IpFilter | None) -> None:
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
        overrides: list[ApplianceCredentialOverride] | None = None,
    ) -> None:
        for appliance in self._appliances:
            appliance.username = default_username
            appliance.password = default_password
            for cred in overrides or []:
                cidr = cred.get('cidr')
                username = cred.get('username')
                password = cred.get('password')
                if not cidr or not username or not password:
                    continue
                try:
                    if ipaddress.ip_address(appliance.ip) in ipaddress.ip_network(cidr, strict=False):
                        appliance.username = username
                        appliance.password = password
                        log.debug(
                            "Using CIDR-matched credentials for appliance %s (matched %s)",
                            appliance.ip,
                            cidr,
                        )
                        break
                except (ValueError, TypeError):
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
