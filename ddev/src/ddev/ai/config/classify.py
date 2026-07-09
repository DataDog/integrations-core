# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.loading.files import FileError, MarkdownFile, YamlFile
from ddev.ai.config.models import AgentConfig, FlowEnvelope, PhaseEnvelope, ResourceEnvelope
from ddev.ai.config.registry import BrokenEntry, ValidEntry

if TYPE_CHECKING:
    from ddev.ai.config.loading.files import LoadedFile
    from ddev.ai.config.registry import Entry, ResourceKind


@dataclass(frozen=True)
class ClassifyOutput:
    """The typed entries and file errors produced from one loaded file."""

    entries: list[Entry[Any]] = field(default_factory=list)
    file_errors: list[FileError] = field(default_factory=list)


@dataclass(frozen=True)
class TypeSpec:
    """The kind and on-disk format legal for a given resource ``type`` tag."""

    kind: ResourceKind
    format: Literal["markdown", "yaml"]


TYPE_TABLE: dict[str, TypeSpec] = {
    "agent": TypeSpec(kind="agent", format="markdown"),
    "prompt": TypeSpec(kind="prompt", format="markdown"),
    "goal": TypeSpec(kind="goal", format="markdown"),
    "memory_prompt": TypeSpec(kind="memory_prompt", format="markdown"),
    "phase": TypeSpec(kind="phase", format="yaml"),
    "flow": TypeSpec(kind="flow", format="yaml"),
}

RESOURCE_ADAPTER: TypeAdapter[PhaseEnvelope | FlowEnvelope] = TypeAdapter(ResourceEnvelope)


def meta_without(meta: dict[str, Any], *keys: str) -> dict[str, Any]:
    """A shallow copy of ``meta`` with ``keys`` removed."""
    return {k: v for k, v in meta.items() if k not in keys}


def classify(loaded: LoadedFile) -> ClassifyOutput:
    """Turn one loaded file into zero or more identity-carrying entries.

    Driven by the type table: a resource's kind comes from its ``type`` tag, the format
    gates the legal type subset, and ``name`` is required identity. Touches no filesystem
    and cross-references nothing.
    """
    if isinstance(loaded, MarkdownFile):
        return _classify_markdown(loaded)
    return _classify_yaml(loaded)


def _classify_markdown(loaded: MarkdownFile) -> ClassifyOutput:
    type_ = loaded.meta.get("type")
    if type_ is None:
        return ClassifyOutput()

    spec = TYPE_TABLE.get(type_)
    if spec is None:
        return ClassifyOutput(file_errors=[FileError(loaded.path, f"unknown resource type {type_!r}")])

    if spec.format != "markdown":
        message = f"type {type_!r} is not valid in a Markdown file"
        return ClassifyOutput(file_errors=[FileError(loaded.path, message)])

    name = loaded.meta.get("name")
    if not name:
        message = f"Markdown resource of type {type_!r} is missing required 'name'"
        return ClassifyOutput(file_errors=[FileError(loaded.path, message)])

    entry = _build_markdown_entry(spec.kind, name, loaded)
    return ClassifyOutput(entries=[entry])


def _build_markdown_entry(kind: ResourceKind, name: str, loaded: MarkdownFile) -> Entry[Any]:
    if kind != "agent":
        return ValidEntry(kind=kind, name=name, config=loaded.body, source_file=loaded.path)

    fields = meta_without(loaded.meta, "type", "name")
    try:
        config = AgentConfig(**fields, system_prompt=loaded.body)
    except ValidationError as e:
        return BrokenEntry(kind="agent", name=name, source_file=loaded.path, error=str(e))
    return ValidEntry(kind="agent", name=name, config=config, source_file=loaded.path)


def _classify_yaml(loaded: YamlFile) -> ClassifyOutput:
    entries: list[Entry[Any]] = []
    file_errors: list[FileError] = []

    for i, item in enumerate(loaded.docs):
        if not isinstance(item, dict) or "type" not in item:
            continue

        type_ = item["type"]
        spec = TYPE_TABLE.get(type_)
        if spec is None or spec.format != "yaml":
            message = f"item {i}: type {type_!r} is not valid in a YAML file"
            file_errors.append(FileError(loaded.path, message))
            continue

        try:
            envelope = RESOURCE_ADAPTER.validate_python(item)
        except (ValidationError, TypeError, ValueError) as e:
            entry_or_error = _recover_broken_yaml_entry(item, spec, loaded.path, i, e)
            if isinstance(entry_or_error, FileError):
                file_errors.append(entry_or_error)
            else:
                entries.append(entry_or_error)
            continue

        entries.append(
            ValidEntry(kind=envelope.type, name=envelope.config.name, config=envelope.config, source_file=loaded.path)
        )

    return ClassifyOutput(entries=entries, file_errors=file_errors)


def _recover_broken_yaml_entry(
    item: dict[str, Any], spec: TypeSpec, path: Path, index: int, error: Exception
) -> Entry[Any] | FileError:
    config = item.get("config")
    name = config.get("name") if isinstance(config, dict) else None
    if name:
        return BrokenEntry(kind=spec.kind, name=name, source_file=path, error=str(error))
    return FileError(path, f"item {index}: {error}")
