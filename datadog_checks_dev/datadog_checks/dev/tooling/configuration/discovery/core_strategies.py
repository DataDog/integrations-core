# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any

from .registry import strategy


@strategy(
    name='from_ports',
    provides=('port',),
    valid_fields=frozenset({'strategy', 'port_hints', 'candidates'}),
    context_fields={'port': frozenset({'name', 'number'})},
)
def from_ports(stanza: dict[str, Any], index: int) -> list[str]:
    """Generate Python source lines for a from_ports strategy stanza."""
    port_hints = stanza.get('port_hints', [])
    candidates = stanza.get('candidates', [])
    lines = [
        f'    # discovery[{index}]: from_ports',
        f'    for port in candidate_ports(service, {port_hints!r}):',
        "        ctx = {'port': port}",
    ]
    for candidate in candidates:
        lines.append('        instance = InstanceConfig(')
        for field_name, template in candidate.items():
            if '{' in str(template):
                rendered = f"'{template}'.format(service=service, **ctx)"
            else:
                rendered = repr(template)
            lines.append(f'            {field_name}={rendered},')
        lines.append("        ).model_dump(mode='json', exclude_none=True)")
        lines.append("        yield {'init_config': shared, 'instances': [instance]}")
    return lines
