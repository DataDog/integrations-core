# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from ddev.testing.selection import EnvironmentCatalog
from ddev.utils.hatch import Environment


def make_catalog(configs: dict[str, dict[str, Any]], aliases: dict[str, list[str]] | None = None) -> EnvironmentCatalog:
    defaults = {'type': 'virtual', 'test-env': True, 'e2e-env': True, 'benchmark-env': False, 'latest-env': False}
    return EnvironmentCatalog(
        {name: Environment(name=name, **(defaults | config)) for name, config in configs.items()}, aliases or {}
    )
