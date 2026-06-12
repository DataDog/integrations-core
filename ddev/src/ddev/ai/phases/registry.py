# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import importlib
import inspect
from pathlib import Path

from ddev.ai.config.errors import FlowConfigError
from ddev.ai.phases.base import Phase


class PhaseRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, type[Phase]] = {}

    def register(self, name: str, phase_cls: type[Phase]) -> None:
        self._registry[name] = phase_cls

    def known_names(self) -> list[str]:
        return sorted(self._registry)

    def get(self, name: str) -> type[Phase]:
        if name not in self._registry:
            raise ValueError(f"Unknown phase type: {name!r}. Known: {self.known_names()}")
        return self._registry[name]


def discover_and_register_phases(
    registry: PhaseRegistry,
    phases_dir: Path,
    import_prefix: str,
) -> None:
    """Import every non-private *.py in phases_dir and register Phase subclasses.

    Modules are imported by dotted path: ``{import_prefix}.{file_stem}``. The
    caller is responsible for choosing the right pair (dir, prefix). Import
    errors are fatal — a syntax error in any discovered module aborts startup.
    """
    for py_file in phases_dir.glob("*.py"):
        if py_file.stem.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{import_prefix}.{py_file.stem}")
        except Exception as e:
            raise FlowConfigError(f"Failed to import phase module '{py_file.stem}': {e}") from e
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Phase) and not inspect.isabstract(obj) and obj.__module__ == module.__name__:
                registry.register(obj.__name__, obj)
