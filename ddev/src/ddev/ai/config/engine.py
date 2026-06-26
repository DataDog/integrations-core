# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.md import parse_md_file
from ddev.ai.config.models import AgentConfig, FlowConfig, PhaseConfig, ResourceEnvelope


class ConfigStatus(StrEnum):
    OK = "ok"
    BROKEN = "broken"


@dataclass
class RegistryEntry[C]:
    config: C | None
    source_file: Path
    status: ConfigStatus
    error: str | None = None
    overridden: list[Path] = field(default_factory=list)


@dataclass
class ConfigConflict:
    name: str
    type: str
    sources: list[Path]


class PhaseRegistry(Protocol):
    def contains(self, name: str) -> bool: ...


RESOURCE_ADAPTER: TypeAdapter[Any] = TypeAdapter(ResourceEnvelope)

PROMPT_TYPES = {"prompt", "goal", "memory"}


class ConfigurationEngine:
    def __init__(
        self,
        core_dir: Path,
        user_dirs: list[str | Path],
        phase_registry: PhaseRegistry,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._phase_registry = phase_registry

        resolved_user_dirs = self._resolve_user_dirs(user_dirs)

        self._agents: dict[str, RegistryEntry[AgentConfig]] = {}
        self._phases: dict[str, RegistryEntry[PhaseConfig]] = {}
        self._flows: dict[str, RegistryEntry[FlowConfig]] = {}
        self._prompts: dict[str, RegistryEntry[str]] = {}
        self._goals: dict[str, RegistryEntry[str]] = {}
        self._memories: dict[str, RegistryEntry[str]] = {}

        for base_dir in [core_dir, *resolved_user_dirs]:
            self._scan_dir(base_dir)

    def _resolve_user_dirs(self, user_dirs: list[str | Path]) -> list[Path]:
        resolved = []
        for d in user_dirs:
            p = Path(d).expanduser().resolve()
            if not p.is_dir():
                raise FlowConfigError(f"User config directory does not exist or is not a directory: {p}")
            resolved.append(p)
        return resolved

    def _scan_dir(self, base_dir: Path) -> None:
        for path in sorted(base_dir.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in {".yaml", ".yml"}:
                self._dispatch_yaml(path)
            elif suffix == ".md":
                parent_name = path.parent.name
                if parent_name == "agents":
                    self._dispatch_agent_md(path)
                elif parent_name == "prompts":
                    self._dispatch_prompt_md(path)

    def _dispatch_yaml(self, path: Path) -> None:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as e:
            key = path.stem
            self._phases[key] = RegistryEntry(config=None, source_file=path, status=ConfigStatus.BROKEN, error=str(e))
            return

        if not isinstance(raw, list):
            key = path.stem
            self._phases[key] = RegistryEntry(
                config=None,
                source_file=path,
                status=ConfigStatus.BROKEN,
                error=f"{path}: top-level YAML document must be a list",
            )
            return

        for i, item in enumerate(raw):
            self._dispatch_yaml_item(path, item, i)

    def _dispatch_yaml_item(self, path: Path, item: Any, index: int) -> None:
        try:
            envelope = RESOURCE_ADAPTER.validate_python(item)
        except (ValidationError, TypeError, ValueError) as e:
            raw_name = item.get("config", {}).get("name") if isinstance(item, dict) else None
            key = raw_name if raw_name else f"{path.stem}[{index}]"
            entry: RegistryEntry[Any] = RegistryEntry(
                config=None, source_file=path, status=ConfigStatus.BROKEN, error=str(e)
            )
            raw_type = item.get("type") if isinstance(item, dict) else None
            if raw_type == "flow":
                self._flows[key] = entry
            else:
                self._phases[key] = entry
            return

        entry_ok: RegistryEntry[Any] = RegistryEntry(config=envelope.config, source_file=path, status=ConfigStatus.OK)
        if envelope.type == "phase":
            self._phases[envelope.config.name] = entry_ok
        elif envelope.type == "flow":
            self._flows[envelope.config.name] = entry_ok

    def _dispatch_agent_md(self, path: Path) -> None:
        stem = path.stem
        try:
            meta, body = parse_md_file(path)
        except FlowConfigError as e:
            self._agents[stem] = RegistryEntry(config=None, source_file=path, status=ConfigStatus.BROKEN, error=str(e))
            return

        if meta.get("type") != "agent":
            self._agents[stem] = RegistryEntry(
                config=None,
                source_file=path,
                status=ConfigStatus.BROKEN,
                error=f"{path}: expected type 'agent', got {meta.get('type')!r}",
            )
            return

        fm = {k: v for k, v in meta.items() if k != "type"}
        fm["system_prompt"] = body
        try:
            config = AgentConfig.model_validate(fm)
        except ValidationError as e:
            self._agents[stem] = RegistryEntry(config=None, source_file=path, status=ConfigStatus.BROKEN, error=str(e))
            return

        self._agents[stem] = RegistryEntry(config=config, source_file=path, status=ConfigStatus.OK)

    def _dispatch_prompt_md(self, path: Path) -> None:
        stem = path.stem
        try:
            meta, body = parse_md_file(path)
        except FlowConfigError as e:
            self._prompts[stem] = RegistryEntry(config=None, source_file=path, status=ConfigStatus.BROKEN, error=str(e))
            return

        file_type = meta.get("type")
        if file_type not in PROMPT_TYPES:
            self._prompts[stem] = RegistryEntry(
                config=None,
                source_file=path,
                status=ConfigStatus.BROKEN,
                error=f"{path}: expected type in {PROMPT_TYPES!r}, got {file_type!r}",
            )
            return

        entry: RegistryEntry[str] = RegistryEntry(config=body, source_file=path, status=ConfigStatus.OK)
        if file_type == "prompt":
            self._prompts[stem] = entry
        elif file_type == "goal":
            self._goals[stem] = entry
        elif file_type == "memory":
            self._memories[stem] = entry
