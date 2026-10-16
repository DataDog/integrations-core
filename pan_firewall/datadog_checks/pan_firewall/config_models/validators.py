# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
import re
from typing import Any


def check_instance(model: Any) -> Any:
    """Validate the combinations of options that the spec cannot express."""
    firewalls = list(model.firewalls or ())
    credentials = list(model.firewall_credentials or ())

    _check_mode(model, firewalls)
    _check_panorama_auth(model)
    _check_firewalls(firewalls)
    _check_credentials(credentials)
    _check_discovery_filters(model)
    _check_rule_filter(model)
    for ip in firewalls:
        if find_credential(ip, credentials) is None:
            raise ValueError(f'No entry in `firewall_credentials` matches the firewall `{ip}`')

    return model


def find_credential(ip: str, credentials: list[Any]) -> Any | None:
    """Return the first credential entry whose `cidr` contains `ip`; an entry without `cidr` matches every IP."""
    address = ipaddress.ip_address(ip)
    for entry in credentials:
        if entry.cidr is None or address in ipaddress.ip_network(entry.cidr, strict=False):
            return entry
    return None


def _check_mode(model: Any, firewalls: list[str]) -> None:
    if firewalls and model.panorama_host:
        raise ValueError('Set either `firewalls` or `panorama_host`, not both')
    if not firewalls and not model.panorama_host:
        raise ValueError('One of `firewalls` or `panorama_host` is required')


def _check_panorama_auth(model: Any) -> None:
    if not model.panorama_host:
        return
    has_login = bool(model.panorama_username and model.panorama_password)
    has_key = bool(model.panorama_api_key)
    if has_login == has_key:
        raise ValueError(
            '`panorama_host` requires either `panorama_username` and `panorama_password`, or `panorama_api_key`'
        )


def _check_firewalls(firewalls: list[str]) -> None:
    seen = set()
    for ip in firewalls:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f'`firewalls` entry `{ip}` is not a valid IP address') from None
        if address in seen:
            raise ValueError(f'`firewalls` entry `{ip}` is duplicated')
        seen.add(address)


def _check_credentials(credentials: list[Any]) -> None:
    for index, entry in enumerate(credentials):
        has_login = bool(entry.username and entry.password)
        has_key = bool(entry.api_key)
        if has_login == has_key or (has_key and (entry.username or entry.password)):
            raise ValueError(
                f'`firewall_credentials` entry {index} must set either `username` and `password`, or `api_key`'
            )
        if entry.cidr is not None:
            try:
                ipaddress.ip_network(entry.cidr, strict=False)
            except ValueError:
                raise ValueError(
                    f'`firewall_credentials` entry {index} has an invalid `cidr`: `{entry.cidr}`'
                ) from None


def _check_discovery_filters(model: Any) -> None:
    filters = model.firewall_ips
    for field in ('include', 'exclude'):
        for pattern in (getattr(filters, field) or ()) if filters else ():
            try:
                ipaddress.ip_network(pattern, strict=False)
            except ValueError:
                raise ValueError(f'`firewall_ips.{field}` entry `{pattern}` is not an IP address or CIDR') from None


def _check_rule_filter(model: Any) -> None:
    for pattern in model.security_rule_filter or ():
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(
                f'`security_rule_filter` entry `{pattern}` is not a valid regular expression: {e}'
            ) from None
