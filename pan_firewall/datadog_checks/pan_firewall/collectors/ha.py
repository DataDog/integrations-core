# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""High availability (`show high-availability all`): the local HA state, kept for the other collectors.

The HA link counters are not collected yet (Task 5.1), so this collector never returns samples.
"""

from __future__ import annotations

from datadog_checks.pan_firewall.xml_utils import text

from . import CollectContext, Sample, register, warn_once

HA_CMD = '<show><high-availability><all/></high-availability></show>'


@register('ha')
def collect_ha(ctx: CollectContext) -> list[Sample]:
    """Set `ctx.state.ha_state`, None when HA is off. The enabled-HA path is unverified until lab capture L1."""
    root = ctx.client.op(HA_CMD)
    if (text(root, 'result/enabled') or '').lower() != 'yes':
        ctx.state.ha_state = None
        return []
    ctx.state.ha_state = text(root, 'result/group/local-info/state')
    warn_once(ctx, 'ha', 'high availability is enabled; the HA link counters are not supported yet')
    return []
