# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.e2e.agent.interface import AgentInterface
    from ddev.integration.core import Integration
    from ddev.utils.fs import Path


def create_agent(
    app: Application,
    integration: Integration,
    environment: str,
    metadata: dict[str, Any],
    config_file: Path,
) -> AgentInterface:
    from ddev.e2e.constants import DEFAULT_AGENT_TYPE, E2EMetadata

    agent_type = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)
    return get_agent_interface(agent_type)(app, integration, environment, metadata, config_file)


def get_agent_interface(agent_type: str) -> type[AgentInterface]:
    if agent_type == "docker":
        from ddev.e2e.agent.docker import DockerAgent

        return DockerAgent

    if agent_type == "vagrant":
        from ddev.e2e.agent.vagrant import VagrantAgent

        return VagrantAgent

    if agent_type == "kubernetes":
        from ddev.e2e.agent.kubernetes import KubernetesAgent

        return KubernetesAgent

    raise NotImplementedError(f"Unsupported Agent type: {agent_type}")
