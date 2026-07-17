# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from types import SimpleNamespace

from datadog_checks.base.utils.discovery import Port, Service, candidate_ports, discovery_strategy

HTTPS_PORT_NUMBERS = frozenset({443, 8443})
HTTPS_PORT_NAME_MARKERS = ('https', 'ssl', 'tls')


def is_https_port(port: Port) -> bool:
    name = port.name.lower()
    return port.number in HTTPS_PORT_NUMBERS or any(marker in name for marker in HTTPS_PORT_NAME_MARKERS)


@discovery_strategy(provides=('endpoint',))
def from_nginx_ports(service: Service, port_hints: list[int]):
    for port in candidate_ports(service, port_hints):
        scheme = 'https' if is_https_port(port) else 'http'
        yield {'endpoint': SimpleNamespace(scheme=scheme, port=port)}
