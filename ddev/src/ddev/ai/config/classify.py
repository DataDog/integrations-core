# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.loading.files import FileError, MarkdownFile, YamlFile
from ddev.ai.config.models import NAME_PATTERN, AgentConfig, FlowEnvelope, PhaseEnvelope, ResourceEnvelope
from ddev.ai.config.registry import BrokenEntry, ResourceKind, ValidEntry

if TYPE_CHECKING:
    from collections.abc import Callable

    from ddev.ai.agent.registry import AgentProviderRegistry
    from ddev.ai.config.loading.files import LoadedFile
    from ddev.ai.config.registry import Entry


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
    ResourceKind.AGENT: TypeSpec(kind=ResourceKind.AGENT, format="markdown"),
    ResourceKind.PROMPT: TypeSpec(kind=ResourceKind.PROMPT, format="markdown"),
    ResourceKind.GOAL: TypeSpec(kind=ResourceKind.GOAL, format="markdown"),
    ResourceKind.MEMORY_PROMPT: TypeSpec(kind=ResourceKind.MEMORY_PROMPT, format="markdown"),
    ResourceKind.PHASE: TypeSpec(kind=ResourceKind.PHASE, format="yaml"),
    ResourceKind.FLOW: TypeSpec(kind=ResourceKind.FLOW, format="yaml"),
}

RESOURCE_ADAPTER: TypeAdapter[PhaseEnvelope | FlowEnvelope] = TypeAdapter(ResourceEnvelope)


def meta_without(meta: dict[str, Any], *keys: str) -> dict[str, Any]:
    """A shallow copy of ``meta`` with ``keys`` removed."""
    return {k: v for k, v in meta.items() if k not in keys}


def _build_agent(loaded: MarkdownFile, provider_registry: AgentProviderRegistry) -> AgentConfig:
    data = meta_without(loaded.meta, "type", "name")
    data["system_prompt"] = loaded.body
    return AgentConfig.model_validate(data, context={"provider_registry": provider_registry})


def _build_body(loaded: MarkdownFile) -> str:
    return loaded.body


# Each body-bearing markdown kind maps to the builder that turns its file into a config.
MARKDOWN_BUILDERS: dict[ResourceKind, Callable[[MarkdownFile], Any]] = {
    ResourceKind.PROMPT: _build_body,
    ResourceKind.GOAL: _build_body,
    ResourceKind.MEMORY_PROMPT: _build_body,
}


def classify(
    loaded: LoadedFile,
    *,
    provider_registry: AgentProviderRegistry,
) -> ClassifyOutput:
    """Turn one loaded file into zero or more identity-carrying entries.

    Driven by the type table: a resource's kind comes from its ``type`` tag, the format
    gates the legal type subset, and ``name`` is required identity. Touches no filesystem
    and cross-references nothing.
    """
    if isinstance(loaded, MarkdownFile):
        return _classify_markdown(loaded, provider_registry)
    return _classify_yaml(loaded)


def _classify_markdown(
    loaded: MarkdownFile,
    provider_registry: AgentProviderRegistry,
) -> ClassifyOutput:
    type_ = loaded.meta.get("type")
    if type_ is None:
        return ClassifyOutput()

    if not isinstance(type_, str):
        message = f"resource type must be a string, got {type(type_).__name__}"
        return ClassifyOutput(file_errors=[FileError(loaded.path, message)])

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
    if not isinstance(name, str) or not re.match(NAME_PATTERN, name):
        message = f"Markdown resource of type {type_!r} has invalid name {name!r}"
        return ClassifyOutput(file_errors=[FileError(loaded.path, message)])

    entry = _build_markdown_entry(spec.kind, name, loaded, provider_registry)
    return ClassifyOutput(entries=[entry])


def _build_markdown_entry(
    kind: ResourceKind,
    name: str,
    loaded: MarkdownFile,
    provider_registry: AgentProviderRegistry,
) -> Entry[Any]:
    try:
        config = (
            _build_agent(loaded, provider_registry) if kind is ResourceKind.AGENT else MARKDOWN_BUILDERS[kind](loaded)
        )
    except ValidationError as e:
        return BrokenEntry(kind=kind, name=name, source_file=loaded.path, error=str(e))
    return ValidEntry(kind=kind, name=name, config=config, source_file=loaded.path)


def _classify_yaml(loaded: YamlFile) -> ClassifyOutput:
    entries: list[Entry[Any]] = []
    file_errors: list[FileError] = []

    for i, item in enumerate(loaded.docs):
        if not isinstance(item, dict) or "type" not in item:
            continue

        type_ = item["type"]
        if not isinstance(type_, str):
            message = f"item {i}: resource type must be a string, got {type(type_).__name__}"
            file_errors.append(FileError(loaded.path, message))
            continue

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
            ValidEntry(kind=spec.kind, name=envelope.config.name, config=envelope.config, source_file=loaded.path)
        )

    return ClassifyOutput(entries=entries, file_errors=file_errors)


def _recover_broken_yaml_entry(
    item: dict[str, Any], spec: TypeSpec, path: Path, index: int, error: Exception
) -> Entry[Any] | FileError:
    config = item.get("config")
    name = config.get("name") if isinstance(config, dict) else None
    if isinstance(name, str) and name:
        return BrokenEntry(kind=spec.kind, name=name, source_file=path, error=str(error))
    return FileError(path, f"item {index}: {error}")
