# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import ipaddress
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from xml.etree.ElementTree import Element

from .api import PanosClient, new_http
from .auth import Credentials, KeyManager
from .errors import PanosError
from .firewalls import FirewallTarget, resolve_credentials
from .xml_utils import text

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck

    from .config_models.instance import InstanceConfig

DISCOVERY_CMD = '<show><devices><connected/></devices></show>'
# TEMPORARY, to be removed: the lab firewalls report their private IPs to Panorama, and the Agent reaches them at
# public ones. (serial, reported IP) -> polled IP; it matches nothing outside the lab.
LAB_IP_OVERRIDES = {
    ('007955000930601', '10.60.0.10'): '3.13.247.39',
    ('007955000930602', '10.60.0.11'): '3.19.110.163',
}


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
    """Read the `result/devices/entry` elements of a discovery response. An entry without a serial is dropped.

    Only the direct children of `devices` are firewalls: each carries nested `entry` elements (`vsys`,
    `plugin_versions`), and a `Total Connected Devices` text node follows the last one.
    """
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

    When Panorama cannot be queried, the last list it returned (kept in the persistent cache, without any
    credential) is used instead. It reports its own reachability as `panorama.can_connect`.
    """

    def __init__(self, check: AgentCheck, config: InstanceConfig):
        self._check = check
        self._config = config
        # The validator refuses Panorama mode without `panorama_host`.
        self._host = cast(str, config.panorama_host)
        self._cache_key = f'panorama_firewalls:{self._host}'
        http = new_http(check, config)
        credentials = Credentials(config.panorama_username, config.panorama_password, config.panorama_api_key)
        self._keys = KeyManager(http, self._host, credentials)
        self._client = PanosClient(http, self._host, self._keys, check.log)
        self._last_cached: str | None = None
        self._warned: set[str] = set()

    def list_firewalls(self) -> list[FirewallTarget]:
        # One keygen attempt per run after a rejected one (the KeyManager latches until reset).
        self._keys.reset_failure()
        self._client.take_stats()
        devices = self._discover()
        self._check.gauge('panorama.can_connect', 0 if devices is None else 1, tags=self._tags())
        if devices is None:
            devices = self._load_cached()
        return self._targets(devices or [])

    def _discover(self) -> list[DiscoveredFirewall] | None:
        """Return the connected-devices list, or None (logged) when the call fails for any reason."""
        try:
            devices = parse_devices(self._client.op(DISCOVERY_CMD))
        except PanosError as e:
            # The message says whether the credentials were rejected.
            self._check.log.warning(
                'pan_firewall: could not get the connected devices from Panorama %s: %s', self._host, e
            )
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
        raw = json.dumps([dataclasses.asdict(d) for d in devices])
        if raw != self._last_cached:
            self._check.write_persistent_cache(self._cache_key, raw)
            self._last_cached = raw

    def _load_cached(self) -> list[DiscoveredFirewall] | None:
        raw = self._check.read_persistent_cache(self._cache_key)
        try:
            devices = [DiscoveredFirewall(**d) for d in json.loads(raw)] if raw else None
        except (ValueError, TypeError) as e:
            self._check.log.debug('pan_firewall: ignoring the cached Panorama firewall list: %s', e)
            devices = None
        if devices is None:
            self._check.log.warning(
                'pan_firewall: Panorama %s is unreachable and there are no discovered firewalls to fall back on',
                self._host,
            )
        else:
            self._check.log.warning(
                'pan_firewall: Panorama %s is unreachable; polling the %d firewalls of the last discovery',
                self._host,
                len(devices),
            )
        return devices

    def _targets(self, devices: list[DiscoveredFirewall]) -> list[FirewallTarget]:
        targets: dict[str, FirewallTarget] = {}
        for firewall in devices:
            if not firewall.connected:
                self._check.log.debug(
                    'pan_firewall: firewall %s is not connected to Panorama, skipping it', firewall.serial
                )
                continue
            target = self._target(firewall)
            if target is None:
                continue
            if target.ip in targets:
                self._warn_once(
                    f'duplicate:{target.ip}',
                    'pan_firewall: firewalls %s and %s are both polled at %s; only the first is polled',
                    targets[target.ip].serial,
                    firewall.serial,
                    target.ip,
                )
                continue
            targets[target.ip] = target
        return list(targets.values())

    def _target(self, firewall: DiscoveredFirewall) -> FirewallTarget | None:
        polled = LAB_IP_OVERRIDES.get((firewall.serial, firewall.ip_address or ''), firewall.ip_address)
        address = _parse_ip(polled)
        if address is None:
            self._warn_once(
                f'no-ip:{firewall.serial}',
                'pan_firewall: firewall %s has no usable IP address (Panorama reports `%s`), skipping it',
                firewall.serial,
                polled or '',
            )
            return None
        ip = str(address)
        if not self._passes_filters(address):
            self._check.log.debug(
                'pan_firewall: firewall %s at %s is filtered out by `firewall_ips`', firewall.serial, ip
            )
            return None
        credentials = resolve_credentials(ip, self._config.firewall_credentials or ())
        if credentials is None:
            self._warn_once(
                f'credentials:{ip}',
                'pan_firewall: no entry in `firewall_credentials` matches the firewall %s at %s, skipping it',
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
        )

    def _passes_filters(self, address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        filters = self._config.firewall_ips
        if filters is None:
            return True
        if any(address in ipaddress.ip_network(p, strict=False) for p in filters.exclude or ()):
            return False
        include = filters.include or ()
        return not include or any(address in ipaddress.ip_network(p, strict=False) for p in include)

    def _warn_once(self, key: str, message: str, *args: object) -> None:
        # The discovery runs every check run: a persistent condition is warned about once, not every run.
        if key not in self._warned:
            self._warned.add(key)
            self._check.log.warning(message, *args)


def _parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value or '')
    except ValueError:
        return None
