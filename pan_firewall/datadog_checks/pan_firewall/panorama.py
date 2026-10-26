# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import ipaddress
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from .api import PanosClient
from .auth import Credentials, KeyManager
from .errors import PanosError
from .firewalls import FirewallTarget, resolve_credentials
from .log_utils import warn_once
from .xml_utils import text

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck

    from .config_models.instance import InstanceConfig

DISCOVERY_CMD = '<show><devices><connected/></devices></show>'


@dataclass(frozen=True)
class DiscoveredFirewall:
    """A firewall as Panorama's `show devices connected` lists it. `ip_address` is the raw text, None if absent."""

    serial: str
    hostname: str | None
    ip_address: str | None
    model: str | None
    family: str | None
    sw_version: str | None
    connected: bool


def parse_devices(root: Element) -> list[DiscoveredFirewall]:
    firewalls = []
    for entry in root.findall('./result/devices/entry'):
        serial = text(entry, 'serial')
        if serial is None:
            continue
        firewalls.append(
            DiscoveredFirewall(
                serial=serial,
                hostname=text(entry, 'hostname'),
                ip_address=text(entry, 'ip-address'),
                model=text(entry, 'model'),
                family=text(entry, 'family'),
                sw_version=text(entry, 'sw-version'),
                connected=(text(entry, 'connected') or '').lower() == 'yes',
            )
        )
    return firewalls


class PanoramaFirewallSource:
    """The firewalls a Panorama manages, discovered on every run and polled directly.

    When Panorama cannot be queried, the last list it returned (cached, without credentials) is used, however old:
    the firewalls are polled directly, and `panorama.can_connect` reports the outage.
    """

    def __init__(self, check: AgentCheck, config: InstanceConfig, host: str):
        self._check = check
        self._config = config
        self._host = host
        self._cache_key = f'panorama_firewalls:{self._host}'
        credentials = Credentials(config.panorama_username, config.panorama_password, config.panorama_api_key)
        self._client = PanosClient(check.http, self._host, KeyManager(check.http, self._host, credentials), check.log)
        self._ip_overrides = dict(config.firewall_ip_overrides or {})
        self._warned: set[str] = set()

    def list_firewalls(self) -> list[FirewallTarget]:
        self._client.start_run()
        devices = self._discover()
        self._check.gauge('panorama.can_connect', 0 if devices is None else 1, tags=self._tags())
        if devices is not None:
            return self._targets(devices)
        cached = self._load_cached()
        if cached is None:
            return []
        devices, discovered = cached
        targets = self._targets(devices)
        self._check.log.warning(
            'Panorama %s is unreachable; polling %d of the %d firewalls of the last discovery, at %s',
            self._host,
            len(targets),
            len(devices),
            datetime.fromtimestamp(discovered, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        )
        return targets

    def _discover(self) -> list[DiscoveredFirewall] | None:
        try:
            devices = parse_devices(self._client.op(DISCOVERY_CMD))
        except PanosError as e:
            # The message says whether the credentials were rejected.
            self._check.log.warning('could not get the connected devices from Panorama %s: %s', self._host, e)
            return None
        self._store(devices)
        return devices

    def _tags(self) -> list[str]:
        return [
            f'device_namespace:{self._config.namespace or "default"}',
            f'panorama_host:{self._host}',
            *(self._config.tags or ()),
        ]

    def _store(self, devices: list[DiscoveredFirewall]) -> None:
        raw = json.dumps({'discovered': time.time(), 'firewalls': [dataclasses.asdict(d) for d in devices]})
        self._check.write_persistent_cache(self._cache_key, raw)

    def _load_cached(self) -> tuple[list[DiscoveredFirewall], float] | None:
        """The last discovered firewalls and the time (epoch seconds) they were discovered, if usable."""
        raw = self._check.read_persistent_cache(self._cache_key)
        try:
            if raw:
                data = json.loads(raw)
                return [DiscoveredFirewall(**d) for d in data['firewalls']], float(data['discovered'])
        except (ValueError, TypeError, KeyError) as e:
            # Also the old format (a bare list).
            self._check.log.debug('ignoring the cached Panorama firewall list: %s', e)
        self._check.log.warning(
            'Panorama %s is unreachable and there are no discovered firewalls to fall back on',
            self._host,
        )
        return None

    def _targets(self, devices: list[DiscoveredFirewall]) -> list[FirewallTarget]:
        targets: dict[str, FirewallTarget] = {}
        for firewall in devices:
            if not firewall.connected:
                self._check.log.debug('firewall %s is not connected to Panorama, skipping it', firewall.serial)
                continue
            target = self._target(firewall)
            if target is None:
                continue
            if target.ip in targets:
                self._warn_once(
                    f'duplicate_ip:{firewall.serial}',
                    'firewalls %s and %s are both polled at %s; only the first is polled',
                    targets[target.ip].serial,
                    firewall.serial,
                    target.ip,
                )
                continue
            targets[target.ip] = target
        return list(targets.values())

    def _target(self, firewall: DiscoveredFirewall) -> FirewallTarget | None:
        polled = self._ip_overrides.get(firewall.ip_address or '', firewall.ip_address)
        address = _parse_ip(polled)
        if address is None:
            self._warn_once(
                f'no_ip:{firewall.serial}',
                'firewall %s has no usable IP address (Panorama reports `%s`), skipping it',
                firewall.serial,
                polled or '',
            )
            return None
        ip = str(address)
        if not self._passes_filters(address):
            self._check.log.debug('firewall %s at %s is filtered out by `firewall_ips`', firewall.serial, ip)
            return None
        credentials = resolve_credentials(ip, self._config.firewall_credentials or ())
        if credentials is None:
            self._warn_once(
                f'no_credentials:{firewall.serial}',
                'no entry in `firewall_credentials` matches the firewall %s at %s, skipping it',
                firewall.serial,
                ip,
            )
            return None
        return FirewallTarget(
            ip=ip,
            credentials=credentials,
            serial=firewall.serial,
            hostname=firewall.hostname,
            family=firewall.family,
            model=firewall.model,
            sw_version=firewall.sw_version,
            panorama_host=self._host,
        )

    def _warn_once(self, key: str, msg: str, *args: object) -> None:
        warn_once(self._check.log, self._warned, key, msg, *args)

    def _passes_filters(self, address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        filters = self._config.firewall_ips
        if filters is None:
            return True
        if any(address in ipaddress.ip_network(p, strict=False) for p in filters.exclude or ()):
            return False
        include = filters.include or ()
        return not include or any(address in ipaddress.ip_network(p, strict=False) for p in include)


def _parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value or '')
    except ValueError:
        return None
