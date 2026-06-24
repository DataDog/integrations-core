# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy


@pytest.fixture
def run_resources(tmp_path) -> RunResources:
    return RunResources(
        agent_clients={},
        file_access_policy=FileAccessPolicy(write_root=tmp_path),
        agents={
            "a": AgentConfig(name="a"),
            "b": AgentConfig(name="b"),
        },
        callbacks=Callbacks(),
    )


def test_file_registry_getter_is_idempotent(run_resources: RunResources) -> None:
    assert run_resources.file_registry is run_resources.file_registry


def test_agent_config_unknown_name_raises(run_resources: RunResources) -> None:
    with pytest.raises(ResourceUnavailableError, match="No agent definition named 'missing'"):
        run_resources.agent_config("missing")


def test_agent_config_known_name_returns_config(run_resources: RunResources) -> None:
    config = run_resources.agent_config("a")
    assert config.name == "a"
