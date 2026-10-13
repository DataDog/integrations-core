# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from .constants import DEVICE_VENDOR_TAG, NDM_DEVICE_RESOURCE_TAG, NDM_DEVICE_USER_TAGS_RESOURCE_TAG
from .firewalls import FirewallTarget
from .xml_utils import text


@dataclass
class DeviceIdentity:
    """What the check knows about a firewall, from `show system info`. Persisted as JSON across restarts."""

    serial: str | None
    hostname: str | None
    model: str | None
    family: str | None
    sw_version: str | None
    own_ip: str | None
    multi_vsys: bool | None
    advanced_routing: bool | None
    clock: str | None  # system info <time>, firewall-local


def parse_system_info(root: Element) -> DeviceIdentity:
    """Build the identity from a `<show><system><info/></system></show>` response."""
    system = root.find('./result/system')
    return DeviceIdentity(
        serial=text(system, 'serial'),
        hostname=text(system, 'hostname'),
        model=text(system, 'model'),
        family=text(system, 'family'),
        sw_version=text(system, 'sw-version'),
        own_ip=text(system, 'ip-address'),
        multi_vsys=_on_off(text(system, 'multi-vsys')),
        advanced_routing=_on_off(text(system, 'advanced-routing')),
        clock=text(system, 'time'),
    )


def _on_off(value: str | None) -> bool | None:
    # Anything other than `on`/`off` is unknown, not off: a wrong `multi_vsys:false` would hide vsys.
    return {'on': True, 'off': False}.get(value or '')


def device_ip(target: FirewallTarget) -> str:
    """The `device_ip` tag: the configured IP in static mode, the IP Panorama reports (not the override) otherwise."""
    return target.reported_ip or target.ip


def global_tags(
    identity: DeviceIdentity | None, target: FirewallTarget, namespace: str, user_tags: Iterable[str]
) -> list[str]:
    """Tags on every metric of a firewall. Empty values are left out; the serial-based tags need a known serial.

    `identity` is None before a static firewall first answers; Panorama discovery fills the serial and hostname.
    """
    serial = (identity.serial if identity else None) or target.serial
    hostname = (identity.hostname if identity else None) or target.hostname
    values = {
        'device_namespace': namespace,
        'device_ip': device_ip(target),
        'device_id': serial,
        'device_hostname': hostname,
        'device_serial': serial,
        'device_model': identity.model if identity else None,
        'device_family': identity.family if identity else None,
        'device_vendor': DEVICE_VENDOR_TAG,
        'os_version': identity.sw_version if identity else None,
        'multi_vsys': _bool_tag(identity.multi_vsys) if identity else None,
        'advanced_routing': _bool_tag(identity.advanced_routing) if identity else None,
    }
    tags = [f'{name}:{value}' for name, value in values.items() if value]
    tags.extend(user_tags)
    if serial:
        tags.extend([f'{NDM_DEVICE_RESOURCE_TAG}:{serial}', f'{NDM_DEVICE_USER_TAGS_RESOURCE_TAG}:{serial}'])
    return tags


def _bool_tag(value: bool | None) -> str | None:
    return None if value is None else str(value).lower()


def vsys_list(
    identity: DeviceIdentity, interface_rows: Sequence[Element], configured: Sequence[str] | None
) -> list[str]:
    """The vsys to poll, as `vsysN`: the `vsys` option if set, else detected from `show interface all`.

    `interface_rows` are the `result/ifnet/entry` elements. A multi-vsys firewall whose rows are not known yet (the
    call failed, or the identity came from the cache) falls back to `vsys1`, which always exists.
    """
    if configured:
        return [_normalize_vsys(v) for v in configured]
    if not identity.multi_vsys:
        return ['vsys1']
    detected = {_normalize_vsys(v) for row in interface_rows if (v := text(row, 'vsys'))}
    # By number, so vsys10 sorts after vsys2.
    return sorted(detected, key=lambda v: (len(v), v)) or ['vsys1']


def _normalize_vsys(value: str) -> str:
    value = value.strip()
    return value if value.startswith('vsys') else f'vsys{value}'
