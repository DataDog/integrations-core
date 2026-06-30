# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy


def _resources(tmp_path) -> RunResources:
    return RunResources(
        agent_clients={},
        file_access_policy=FileAccessPolicy(write_root=tmp_path),
        agents={"a": MagicMock(), "b": MagicMock()},
        callbacks=Callbacks(),
    )


def test_agent_config_unknown_name_raises(tmp_path):
    with pytest.raises(ResourceUnavailableError, match="No agent definition named 'missing'"):
        _resources(tmp_path).agent_config("missing")


def test_file_registry_is_a_cached_singleton(tmp_path):
    r = _resources(tmp_path)
    assert r.file_registry is r.file_registry
