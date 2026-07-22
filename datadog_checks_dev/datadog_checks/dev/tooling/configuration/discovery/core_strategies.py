# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any

from .registry import Input, strategy


@strategy(
    'from_ports',
    provides=('port',),
    inputs={'port_hints': Input('array[int]', required=False)},
    runtime_imports=('from datadog_checks.base.utils.discovery import candidate_ports',),
)
def from_ports(stanza: dict[str, Any]) -> list[str]:
    """Open a loop over candidate ports and bind a `ctx` exposing the current `port`."""
    port_hints = stanza.get('port_hints', [])
    return [
        f'    for port in candidate_ports(service, {port_hints!r}):',
        "        ctx = {'port': port}",
    ]


@strategy(
    'from_named_ports',
    provides=('port',),
    inputs={'port_names': Input('array[string]')},
)
def from_named_ports(stanza: dict[str, Any]) -> list[str]:
    """Open a loop over explicitly named service ports and bind a `ctx` exposing the current `port`."""
    port_names = stanza['port_names']
    # Keep generated integrations compatible with the base version that first
    # introduced discovery while preserving the requested name order and
    # deduplicating ports by number.
    return [
        '    seen_ports = set()',
        f'    for port in (port for port_name in dict.fromkeys({port_names!r}) if port_name '
        'for port in service.ports if port.name == port_name):',
        '        if port.number in seen_ports:',
        '            continue',
        '        seen_ports.add(port.number)',
        "        ctx = {'port': port}",
    ]
