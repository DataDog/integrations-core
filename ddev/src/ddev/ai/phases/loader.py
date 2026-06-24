# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import hashlib
import importlib
import inspect
import keyword
import logging
import re
import sys
import types
from pathlib import Path

from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.models import ResolvedFlow
from ddev.ai.constants import CORE_FLOWS_DIR, CORE_PHASES_DIR, CORE_PHASES_PACKAGE
from ddev.ai.phases.base import Phase
from ddev.ai.phases.registry import PhaseRegistry, discover_and_register_phases

ROOT_PACKAGE = "_ddev_user_phases"


def normalize_flow_name(name: str) -> str:
    """Normalize a flow name to a valid Python identifier."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name).lower().strip("_")
    if normalized and normalized[0].isdigit():
        normalized = f"flow_{normalized}"
    return normalized or "flow"


def _ensure_synthetic_package(pkg_name: str, path: Path | None = None) -> None:
    """Create a synthetic package in sys.modules if it does not already exist."""
    if pkg_name in sys.modules:
        return
    module = types.ModuleType(pkg_name)
    module.__package__ = pkg_name
    module.__path__ = [str(path)] if path is not None else []
    sys.modules[pkg_name] = module


def _is_valid_module_stem(stem: str) -> bool:
    return stem.isidentifier() and not keyword.iskeyword(stem)


class PhaseLoader:
    """Discovers phase classes from CORE_PHASES_DIR, CORE_FLOWS_DIR, and user-provided directories."""

    def __init__(
        self,
        user_dirs: list[Path] | None = None,
        logger: logging.Logger | None = None,
        *,
        core_flows_dir: Path = CORE_FLOWS_DIR,
    ) -> None:
        self._base_dirs = [core_flows_dir] + (user_dirs or [])
        self._logger = logger or logging.getLogger(__name__)

    def load(self, resolved: ResolvedFlow) -> PhaseRegistry:
        """Discover all phase classes, validate against resolved flow, return populated registry."""
        registry = PhaseRegistry()
        self._discover(registry, resolved.name)
        self._validate(registry, resolved)
        return registry


    def _discover(self, registry: PhaseRegistry, flow_name: str) -> None:
        self._discover_core(registry)
        self._discover_base_dirs(registry, flow_name)

    def _discover_core(self, registry: PhaseRegistry) -> None:
        discover_and_register_phases(registry, CORE_PHASES_DIR, CORE_PHASES_PACKAGE)

    def _discover_base_dirs(self, registry: PhaseRegistry, flow_name: str) -> None:
        normalized = normalize_flow_name(flow_name)
        for base_dir in self._base_dirs:
            flow_phases = base_dir / flow_name / "phases"
            if flow_phases.is_dir():
                self._load_phases_dir(registry, flow_phases, normalized)
            shared_phases = base_dir / "shared" / "phases"
            if shared_phases.is_dir():
                self._load_phases_dir(registry, shared_phases, "shared")

    def _load_phases_dir(self, registry: PhaseRegistry, phases_dir: Path, flow_pkg_name: str) -> None:
        phases_pkg_name = self._setup_synthetic_packages(flow_pkg_name, phases_dir)
        for py_file in sorted(phases_dir.glob("*.py")):
            stem = py_file.stem
            if stem.startswith("_"):
                continue
            if not _is_valid_module_stem(stem):
                raise FlowConfigError(
                    f"Invalid phase module filename: {py_file.name}\n"
                    f"Phase files must be valid Python module names.\n"
                    f"Use {re.sub(r'[^a-zA-Z0-9]', '_', stem)}.py instead."
                )
            self._import_and_register(registry, phases_pkg_name, stem, phases_dir)

    def _setup_synthetic_packages(self, flow_pkg_name: str, phases_dir: Path) -> str:
        path_hash = hashlib.sha1(str(phases_dir.resolve()).encode()).hexdigest()[:8]
        flow_ns = f"{flow_pkg_name}_{path_hash}"
        _ensure_synthetic_package(ROOT_PACKAGE)
        _ensure_synthetic_package(f"{ROOT_PACKAGE}.{flow_ns}")
        phases_pkg_name = f"{ROOT_PACKAGE}.{flow_ns}.phases"
        _ensure_synthetic_package(phases_pkg_name, phases_dir)
        return phases_pkg_name

    def _import_and_register(self, registry: PhaseRegistry, phases_pkg_name: str, stem: str, phases_dir: Path) -> None:
        module_name = f"{phases_pkg_name}.{stem}"
        file_path = phases_dir / f"{stem}.py"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            hint = ""
            if "No module named" in str(e):
                hint = "\n\nHint: Use relative imports inside phase files:\n\n  from .helpers import helper"
            raise FlowConfigError(f"Failed to import: {file_path}\n\nOriginal error:\n{e}{hint}") from e

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, Phase) or inspect.isabstract(obj):
                continue
            if obj.__module__ != module_name:
                continue
            key = obj.__name__
            if registry.contains(key):
                raise FlowConfigError(f"Duplicate phase type: {key!r}")
            registry.register(key, obj)

    def _validate(self, registry: PhaseRegistry, resolved: ResolvedFlow) -> None:
        for phase_id, phase_config in resolved.phases.items():
            try:
                phase_cls = registry.get(phase_config.class_)
            except ValueError as e:
                raise FlowConfigError(f"Phase {phase_id!r} declares unknown class {phase_config.class_!r}: {e}") from e
            phase_cls.validate_config(phase_id, phase_config, resolved.agents)
