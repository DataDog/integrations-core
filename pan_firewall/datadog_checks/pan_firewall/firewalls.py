# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .auth import Credentials
from .config_models.validators import find_credential

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .config_models.instance import FirewallCredential, InstanceConfig


@dataclass(frozen=True)
class FirewallTarget:
    """A firewall to poll, at `ip` (the configured IP in static mode, the Panorama `ip-address` otherwise). `serial`,
    `hostname`, `family`, `model` and `sw_version` come from Panorama discovery (None in static mode). The firewall's
    own `show system info` takes over `hostname`, `family`, `model` and `sw_version` once it answers.
    """

    ip: str
    credentials: Credentials
    serial: str | None = None
    hostname: str | None = None
    family: str | None = None
    model: str | None = None
    sw_version: str | None = None

    @property
    def poller_key(self) -> tuple[object, ...]:
        """What a poller is built from: a target with another key needs a new poller. The descriptive fields
        (`hostname`, `family`, `model`, `sw_version`) can change on a poller that keeps running."""
        return (self.ip, self.credentials, self.serial)


class FirewallSource(Protocol):
    def list_firewalls(self) -> list[FirewallTarget]: ...


def resolve_credentials(ip: str, entries: Sequence[FirewallCredential]) -> Credentials | None:
    """Return the credentials of the first entry matching `ip`, or None. An entry without `cidr` matches every IP."""
    entry = find_credential(ip, list(entries))
    if entry is None:
        return None
    return Credentials(username=entry.username, password=entry.password, api_key=entry.api_key)


class StaticFirewallSource:
    """The firewalls listed in the `firewalls` option, in config order."""

    def __init__(self, config: InstanceConfig):
        self._targets = []
        for ip in config.firewalls or ():
            credentials = resolve_credentials(ip, config.firewall_credentials or ())
            if credentials is None:
                raise ValueError(f'No entry in `firewall_credentials` matches the firewall `{ip}`')
            self._targets.append(FirewallTarget(ip=ip, credentials=credentials))

    def list_firewalls(self) -> list[FirewallTarget]:
        return list(self._targets)
