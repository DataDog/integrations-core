# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import tomlkit
from pydantic import AfterValidator, Field
from tomlkit import TOMLDocument
from tomlkit.items import Table

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

CONFIG_RELATIVE_PATH = Path(".ddev") / "config.toml"
MANIFEST_PLATFORMS_PATH = ("overrides", "manifest", "platforms")
DISPLAY_NAME_PATH = ("overrides", "display-name")
METRICS_PREFIX_PATH = ("overrides", "metrics-prefix")


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class RegisterIntegrationInput(BaseToolInput):
    platforms: Annotated[
        list[Literal["linux", "windows", "mac_os"]],
        Field(
            description="Operating systems the integration supports.",
            min_length=1,
        ),
        AfterValidator(_dedupe_preserve_order),
    ]
    display_name: Annotated[
        str | None,
        Field(
            default=None,
            description="Human-readable display name. Provide only when it differs from the snake_case folder name.",
        ),
    ]
    metrics_prefix: Annotated[
        str | None,
        Field(
            default=None,
            description="Metric prefix used by the integration. Provide only when the prefix is non-default.",
        ),
    ]


@dataclass(frozen=True)
class _PendingWrite:
    path: tuple[str, ...]
    value: object
    label: str


class RegisterIntegrationTool(BaseTool[RegisterIntegrationInput]):
    """Registers this integration's metadata in the repo-wide configuration so
    build and validation tooling can discover it. The integration is not fully
    shipped until it has been registered — call this once the integration
    directory has been scaffolded."""

    def __init__(self, policy: FileAccessPolicy) -> None:
        self._write_root = policy.write_root

    @property
    def name(self) -> str:
        return "register_integration"

    async def __call__(self, tool_input: RegisterIntegrationInput) -> ToolResult:
        integration = self._write_root.name

        config_path = _find_config(self._write_root)
        if config_path is None:
            return ToolResult(
                success=False,
                error=f"Could not locate {CONFIG_RELATIVE_PATH} walking up from {self._write_root}",
            )

        try:
            document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        except OSError as e:
            return ToolResult(success=False, error=f"Failed to read {config_path}: {e}")
        except tomlkit.exceptions.TOMLKitError as e:
            return ToolResult(success=False, error=f"Failed to parse {config_path}: {e}")

        planned: list[_PendingWrite] = [
            _PendingWrite(MANIFEST_PLATFORMS_PATH, list(tool_input.platforms), "manifest.platforms"),
        ]
        if tool_input.display_name is not None:
            planned.append(_PendingWrite(DISPLAY_NAME_PATH, tool_input.display_name, "display-name"))
        if tool_input.metrics_prefix is not None:
            planned.append(_PendingWrite(METRICS_PREFIX_PATH, tool_input.metrics_prefix, "metrics-prefix"))

        for entry in planned:
            conflict_at = _first_non_table_node(document, entry.path)
            if conflict_at is not None:
                return ToolResult(
                    success=False,
                    error=(
                        f"{entry.label} for {integration!r} cannot be written to {config_path}: "
                        f"{conflict_at} is not a table"
                    ),
                )

        to_write: list[_PendingWrite] = []
        for entry in planned:
            existing = _read_existing(document, entry.path, integration)
            if existing is None:
                to_write.append(entry)
            elif not _equal(existing, entry.value):
                return ToolResult(
                    success=False,
                    error=(
                        f"{entry.label} for {integration!r} already exists with a different value: "
                        f"existing={_unwrap(existing)!r}, requested={entry.value!r}"
                    ),
                )

        for entry in to_write:
            _set_at_path(document, entry.path, integration, entry.value)

        if to_write:
            try:
                config_path.write_text(tomlkit.dumps(document), encoding="utf-8")
            except OSError as e:
                return ToolResult(success=False, error=f"Failed to write {config_path}: {e}")
            written = ", ".join(entry.label for entry in to_write)
            return ToolResult(success=True, data=f"Registered {integration!r} in: {written}")

        sections = ", ".join(entry.label for entry in planned)
        return ToolResult(success=True, data=f"{integration!r} already registered in: {sections}")


def _find_config(start: Path) -> Path | None:
    """Walk up from `start` until a directory contains `.ddev/config.toml`."""
    for candidate in (start, *start.parents):
        config = candidate / CONFIG_RELATIVE_PATH
        if config.is_file():
            return config
    return None


def _first_non_table_node(document: TOMLDocument, path: tuple[str, ...]) -> str | None:
    """Return the dotted prefix of the first non-Table node along `path`, or None if writable."""
    node: object = document
    walked: list[str] = []
    for part in path:
        if not isinstance(node, (TOMLDocument, Table)):
            return ".".join(walked)
        if part not in node:
            return None
        walked.append(part)
        node = node[part]
    if not isinstance(node, (TOMLDocument, Table)):
        return ".".join(walked)
    return None


def _read_existing(document: TOMLDocument, path: tuple[str, ...], key: str) -> object | None:
    node: object = document
    for part in path:
        if not isinstance(node, (TOMLDocument, Table)) or part not in node:
            return None
        node = node[part]
    if not isinstance(node, (TOMLDocument, Table)) or key not in node:
        return None
    return node[key]


def _set_at_path(document: TOMLDocument, path: tuple[str, ...], key: str, value: object) -> None:
    """Set `key = value` inside the table at `path`, creating intermediate tables as needed.

    Assumes the caller has preflighted `path` against the document so every existing
    node along it is a Table — see `_first_non_table_node`.
    """
    node: TOMLDocument | Table = document
    for part in path:
        if part not in node:
            node[part] = tomlkit.table()
        node = node[part]
    node[key] = value


def _equal(existing: object, requested: object) -> bool:
    """Compare a tomlkit-parsed value against the requested Python value.

    tomlkit item types subclass their Python equivalents (e.g. Array extends
    list, String extends str), so `==` already compares correctly. Lists are
    compared element-wise for ordering, which is what we want for platforms.
    """
    if isinstance(requested, list):
        return isinstance(existing, list) and list(existing) == requested
    return existing == requested


def _unwrap(value: object) -> object:
    """Unwrap a tomlkit container to its plain-Python equivalent for display."""
    if isinstance(value, list):
        return list(value)
    return value
