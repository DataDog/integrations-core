# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Annotated, Literal

import tomlkit
from pydantic import Field
from tomlkit import TOMLDocument
from tomlkit.items import Table

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

CONFIG_RELATIVE_PATH = Path(".ddev") / "config.toml"
MANIFEST_PLATFORMS_PATH = ("overrides", "manifest", "platforms")
DISPLAY_NAME_PATH = ("overrides", "display-name")
METRICS_PREFIX_PATH = ("overrides", "metrics-prefix")


class RegisterIntegrationInput(BaseToolInput):
    platforms: Annotated[
        list[Literal["linux", "windows", "mac_os"]],
        Field(
            description="Operating systems the integration supports.",
            min_length=1,
        ),
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

        planned: list[tuple[tuple[str, ...], object, str]] = [
            (MANIFEST_PLATFORMS_PATH, list(tool_input.platforms), "manifest.platforms"),
        ]
        if tool_input.display_name is not None:
            planned.append((DISPLAY_NAME_PATH, tool_input.display_name, "display-name"))
        if tool_input.metrics_prefix is not None:
            planned.append((METRICS_PREFIX_PATH, tool_input.metrics_prefix, "metrics-prefix"))

        to_write: list[tuple[tuple[str, ...], object, str]] = []
        for path, requested, label in planned:
            existing = _read_existing(document, path, integration)
            if existing is None:
                to_write.append((path, requested, label))
            elif not _equal(existing, requested):
                return ToolResult(
                    success=False,
                    error=(
                        f"{label} for {integration!r} already exists with a different value: "
                        f"existing={_unwrap(existing)!r}, requested={requested!r}"
                    ),
                )

        for path, value, _ in to_write:
            _set_at_path(document, path, integration, value)

        if to_write:
            try:
                config_path.write_text(tomlkit.dumps(document), encoding="utf-8")
            except OSError as e:
                return ToolResult(success=False, error=f"Failed to write {config_path}: {e}")

        sections = ", ".join(label for _, _, label in planned)
        return ToolResult(success=True, data=f"Registered {integration!r} in: {sections}")


def _find_config(start: Path) -> Path | None:
    """Walk up from `start` until a directory contains `.ddev/config.toml`."""
    for candidate in (start, *start.parents):
        config = candidate / CONFIG_RELATIVE_PATH
        if config.is_file():
            return config
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
    node: TOMLDocument | Table = document
    for part in path:
        if part not in node:
            node[part] = tomlkit.table()
        child = node[part]
        if not isinstance(child, (TOMLDocument, Table)):
            raise TypeError(f"Expected table at {part!r}, found {type(child).__name__}")
        node = child
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
