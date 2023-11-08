# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.e2e.agent.interface import AgentInterface


def get_agent_interface(agent_type: str) -> type[AgentInterface]:
    if agent_type == 'docker':
        from ddev.e2e.agent.docker import DockerAgent

        return DockerAgent

    raise NotImplementedError(f'Unsupported Agent type: {agent_type}')
