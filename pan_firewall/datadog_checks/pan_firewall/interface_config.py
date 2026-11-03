# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The interface comment and link state, from the interface section of the running config.

Read with an op command, not `type=config`: the read-only role has no XML API Configuration permission, but its
Operational Requests allow `show config running`. The xpath must never be dropped: the whole config holds the admin
password hashes and the IKE pre-shared keys. Only physical ethernet has `link-state`; PAN-OS leaves out the default
(`auto`) and an unset comment.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree.ElementTree import Element

from .xml_utils import text

INTERFACE_CONFIG_CMD = '<show><config><running><xpath>devices/entry/network/interface</xpath></running></config></show>'
LINK_STATE_DOWN = 'down'


@dataclass(frozen=True)
class InterfaceConfig:
    comment: str | None = None
    link_state: str | None = None


def parse_interface_config(root: Element) -> dict[str, InterfaceConfig]:
    """The settings of each interface that has a comment or a link state, by name."""
    config = {}
    for entry in root.iterfind('./result/interface//entry[@name]'):
        comment = text(entry, 'comment')
        link_state = text(entry, 'link-state')
        if comment or link_state:
            config[entry.get('name') or ''] = InterfaceConfig(comment=comment, link_state=link_state)
    return config
