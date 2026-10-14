# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element

from .constants import DEVICE_VENDOR_TAG, NDM_DEVICE_RESOURCE_TAG, NDM_DEVICE_USER_TAGS_RESOURCE_TAG, PARSE_ERROR_CODE
from .errors import PanosApiError
from .firewalls import FirewallTarget
from .xml_utils import text


@dataclass
class DeviceIdentity:
    """What the check knows about a firewall, from `show system info`, persisted as JSON. `clock` is neither compared
    nor persisted, so a refresh that only moves it does not rewrite the cache."""

    serial: str | None
    hostname: str | None
    model: str | None
    family: str | None
    sw_version: str | None
    own_ip: str | None
    multi_vsys: bool | None
    advanced_routing: bool | None
    clock: str | None = field(default=None, compare=False)  # system info <time>, firewall-local

    def to_json(self) -> str:
        data = dataclasses.asdict(self)
        del data['clock']
        return json.dumps(data)

    @classmethod
    def from_json(cls, raw: str) -> DeviceIdentity:
        """Raises ValueError or TypeError for anything `to_json()` did not write."""
        return cls(**json.loads(raw))


def parse_system_info(root: Element) -> DeviceIdentity:
    """Raises PanosApiError for a reply without a serial: it is the device ID, and the device tags need it."""
    system = root.find('./result/system')
    if not text(system, 'serial'):
        raise PanosApiError(PARSE_ERROR_CODE, 'system info has no serial')
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
    """The `device_ip` tag: the polled IP."""
    return target.ip


def global_tags(
    identity: DeviceIdentity | None, target: FirewallTarget, namespace: str, user_tags: Iterable[str]
) -> list[str]:
    """Tags on every metric of a firewall. `identity` is None before a static firewall first answers; until then
    Panorama discovery fills in what it knows."""
    serial = (identity.serial if identity else None) or target.serial
    hostname = (identity.hostname if identity else None) or target.hostname
    values = {
        'device_namespace': namespace,
        'device_ip': device_ip(target),
        'device_id': serial,
        'device_hostname': hostname,
        'device_serial': serial,
        'device_model': (identity.model if identity else None) or target.model,
        'device_family': (identity.family if identity else None) or target.family,
        'device_vendor': DEVICE_VENDOR_TAG,
        'os_version': (identity.sw_version if identity else None) or target.sw_version,
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
    """The vsys to poll: the `vsys` option, else detected from the `show interface all` rows. Without rows, a
    multi-vsys firewall falls back to `vsys1`, which always exists."""
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
