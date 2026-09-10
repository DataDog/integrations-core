# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Per-run copies of ``snapshot`` path inputs.

A snapshot input reaches agents as a path rather than as inlined text, so the file it
points at must not change underneath a run. Every such input is copied into the run
directory once and every phase, task, and goal reviewer resolves the same copy.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from ddev.ai.config.models import ResolvedFlow, RuntimeVariables

INPUTS_DIR_NAME = "inputs"
MANIFEST_NAME = "manifest.yaml"
READ_ONLY_MODE = 0o444


@dataclass(frozen=True)
class SnapshotInput:
    """One input captured for the lifetime of a run."""

    name: str
    source: Path
    path: Path
    sha256: str
    size: int
    captured_at: str
    diverged: bool = False
    """The reused snapshot no longer matches the file the run was launched with."""


def snapshot_path_inputs(
    flow: ResolvedFlow,
    runtime_variables: RuntimeVariables,
    run_dir: Path,
    *,
    resume: bool = False,
) -> tuple[RuntimeVariables, list[SnapshotInput]]:
    """Capture every snapshot input under ``run_dir`` and repoint its variable at the copy.

    On resume an already-captured snapshot is reused rather than re-copied, so a run that
    restarts keeps reading the requirements it started with even if the original file has
    since been edited, moved, or deleted.

    Returns the runtime variables with snapshot inputs rewritten to their copies, plus a
    record per captured input.
    """
    names = [flow_input.name for flow_input in flow.inputs if flow_input.snapshot]
    if not names:
        return runtime_variables, []

    inputs_dir = run_dir / INPUTS_DIR_NAME
    previous = _read_manifest(inputs_dir) if resume else {}

    captured: list[SnapshotInput] = []
    for name in names:
        value = runtime_variables.get(name)
        if not isinstance(value, str) or not value:
            continue
        inputs_dir.mkdir(parents=True, exist_ok=True)
        captured.append(_capture(name, Path(value), inputs_dir, previous.get(name)))

    if not captured:
        return runtime_variables, []

    _write_manifest(inputs_dir, captured)
    return {**runtime_variables, **{item.name: str(item.path) for item in captured}}, captured


def _capture(name: str, source: Path, inputs_dir: Path, previous: dict[str, Any] | None) -> SnapshotInput:
    """Reuse the recorded snapshot when one survives, otherwise copy the source in."""
    if previous is not None:
        path = inputs_dir / str(previous.get("snapshot", ""))
        if path.is_file():
            sha256 = str(previous.get("sha256", ""))
            return SnapshotInput(
                name=name,
                source=Path(str(previous.get("source", source))),
                path=path,
                sha256=sha256,
                size=int(previous.get("size", 0)),
                captured_at=str(previous.get("captured_at", "")),
                diverged=_digest(source) != sha256,
            )

    content = source.read_bytes()
    path = inputs_dir / f"{name}{source.suffix}"
    path.unlink(missing_ok=True)
    path.write_bytes(content)
    path.chmod(READ_ONLY_MODE)
    return SnapshotInput(
        name=name,
        source=source,
        path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
        captured_at=datetime.now(UTC).isoformat(),
    )


def _digest(path: Path) -> str:
    """The source file's digest, or an empty string when it can no longer be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _read_manifest(inputs_dir: Path) -> dict[str, dict[str, Any]]:
    manifest = inputs_dir / MANIFEST_NAME
    if not manifest.is_file():
        return {}
    try:
        loaded = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {name: entry for name, entry in loaded.items() if isinstance(entry, dict)}


def _write_manifest(inputs_dir: Path, captured: list[SnapshotInput]) -> None:
    """Record provenance so a run can be traced back to the file it was launched with."""
    payload = {
        item.name: {
            "source": str(item.source),
            "snapshot": item.path.name,
            "sha256": item.sha256,
            "size": item.size,
            "captured_at": item.captured_at,
        }
        for item in captured
    }
    (inputs_dir / MANIFEST_NAME).write_text(yaml.dump(payload, sort_keys=False), encoding="utf-8")
