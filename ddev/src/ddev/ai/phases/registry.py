# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import importlib
import inspect
from pathlib import Path

from ddev.ai.phases.base import Phase


class PhaseRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, type[Phase]] = {}
        self.import_errors: dict[str, str] = {}

    def register(self, name: str, phase_cls: type[Phase]) -> None:
        self._registry[name] = phase_cls

    def known_names(self) -> list[str]:
        return sorted(self._registry)

    def contains(self, name: str) -> bool:
        return name in self._registry

    def get(self, name: str) -> type[Phase]:
        if name not in self._registry:
            raise ValueError(f"Unknown phase type: {name!r}. Known: {self.known_names()}")
        return self._registry[name]

    def register_from(self, phases_dir: Path, import_prefix: str) -> None:
        """Import every non-private *.py under phases_dir (recursively) and register Phase subclasses.

        Modules are imported by dotted path derived from their path relative to phases_dir, e.g.
        ``openmetrics/inspect_endpoint.py`` -> ``{import_prefix}.openmetrics.inspect_endpoint``.
        Import failures are recorded in import_errors and skipped, not raised. Safe to call more
        than once to accumulate from multiple directories.
        """
        for py_file in sorted(phases_dir.rglob("*.py")):
            rel_parts = py_file.relative_to(phases_dir).with_suffix("").parts
            if any(part.startswith("_") for part in rel_parts):  # skip __init__, _private.py, _private/…
                continue
            module_name = ".".join((import_prefix, *rel_parts))
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError as e:
                # Optional dependency absent (e.g. prometheus-client for the openmetrics phase).
                self.import_errors[module_name] = f"{py_file}: optional dependency missing: {e}"
                continue
            except Exception as e:
                # Module present but failed to import (syntax error, bad top-level statement, …).
                self.import_errors[module_name] = f"{py_file}: failed to import phase module: {e}"
                continue
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Phase) and not inspect.isabstract(obj) and obj.__module__ == module.__name__:
                    self.register(obj.__name__, obj)
