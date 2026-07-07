# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import tomllib
from pathlib import Path


def test_flows_dir_in_wheel_artifacts():
    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    artifacts = data["tool"]["hatch"]["build"]["targets"]["wheel"]["artifacts"]
    assert "src/ddev/ai/flows" in artifacts
