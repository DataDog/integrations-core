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
