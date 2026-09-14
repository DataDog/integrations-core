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
    from collections.abc import Mapping

    from ddev.ai.config.models import ResolvedFlow, RuntimeVariables

INPUTS_DIR_NAME = "inputs"
CAPTURES_DIR_NAME = "files"
MANIFEST_NAME = "manifest.yaml"


@dataclass(frozen=True)
class SnapshotInput:
    """One input captured for the lifetime of a run."""

    name: str
    source: Path
    path: Path
    sha256: str
    size: int
    captured_at: str
    diverged: bool = False  # The reused snapshot no longer matches the file the run was launched with.


@dataclass(frozen=True)
class SnapshotRecord:
    """One input's entry in ``inputs/manifest.yaml``."""

    filename: str
    sha256: str
    size: int
    captured_at: str
    source: Path | None = None  # The path the run was launched with, or ``None`` when the entry omits it.

    @classmethod
    def of(cls, captured: SnapshotInput) -> SnapshotRecord:
        return cls(
            filename=captured.path.name,
            sha256=captured.sha256,
            size=captured.size,
            captured_at=captured.captured_at,
            source=captured.source,
        )

    @classmethod
    def parse(cls, entry: Mapping[str, Any]) -> SnapshotRecord:
        """Read one entry, tolerating the missing keys a truncated manifest can leave."""
        source = entry.get("source")
        return cls(
            filename=str(entry.get("snapshot", "")),
            sha256=str(entry.get("sha256", "")),
            size=int(entry.get("size", 0)),
            captured_at=str(entry.get("captured_at", "")),
            source=Path(str(source)) if source else None,
        )

    def as_payload(self) -> dict[str, Any]:
        return {
            "source": str(self.source) if self.source is not None else "",
            "snapshot": self.filename,
            "sha256": self.sha256,
            "size": self.size,
            "captured_at": self.captured_at,
        }


@dataclass(frozen=True)
class PinnedSnapshot:
    """A snapshot an earlier attempt at a run captured and a resume can reuse."""

    name: str
    source: Path  # The path the run was originally launched with, which may no longer exist.
    path: Path
    captured_at: str


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
    captures_dir = inputs_dir / CAPTURES_DIR_NAME
    previous = _read_manifest(inputs_dir) if resume else {}

    captured: list[SnapshotInput] = []
    for name in names:
        value = runtime_variables.get(name)
        if not isinstance(value, str) or not value:
            continue
        captures_dir.mkdir(parents=True, exist_ok=True)
        captured.append(_capture(name, Path(value), captures_dir, previous.get(name)))

    if not captured:
        return runtime_variables, []

    _write_manifest(inputs_dir, captured)
    return {**runtime_variables, **{item.name: str(item.path) for item in captured}}, captured


def _capture(name: str, source: Path, captures_dir: Path, previous: SnapshotRecord | None) -> SnapshotInput:
    """Reuse the recorded snapshot when one survives, otherwise copy the source in."""
    if previous is not None:
        path = captures_dir / previous.filename
        if path.is_file():
            # Divergence is measured against the path the run was launched with, not the
            # value supplied now: a resume is handed the surviving copy, whose digest
            # trivially matches. A source that has since been deleted reads as diverged.
            recorded_source = previous.source or source
            return SnapshotInput(
                name=name,
                source=recorded_source,
                path=path,
                sha256=previous.sha256,
                size=previous.size,
                captured_at=previous.captured_at,
                diverged=_digest(recorded_source) != previous.sha256,
            )

    content = source.read_bytes()
    path = captures_dir / f"{name}{source.suffix}"
    path.unlink(missing_ok=True)
    path.write_bytes(content)
    return SnapshotInput(
        name=name,
        source=source,
        path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
        captured_at=datetime.now(UTC).isoformat(),
    )


def pinned_snapshot_inputs(run_dir: Path) -> dict[str, PinnedSnapshot]:
    """Return the snapshots an earlier attempt at *run_dir* captured, keyed by input name.

    A resume reuses these instead of collecting the source path again, so a run can
    restart even after the file it was launched with was edited, moved, or deleted.
    Inputs whose copy no longer survives are omitted and must be supplied afresh.
    """
    inputs_dir = run_dir / INPUTS_DIR_NAME
    pinned: dict[str, PinnedSnapshot] = {}
    for name, record in _read_manifest(inputs_dir).items():
        path = inputs_dir / CAPTURES_DIR_NAME / record.filename
        if not path.is_file():
            continue
        pinned[name] = PinnedSnapshot(
            name=name,
            source=record.source or Path(),
            path=path,
            captured_at=record.captured_at,
        )
    return pinned


def _digest(path: Path) -> str:
    """The source file's digest, or an empty string when it can no longer be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _read_manifest(inputs_dir: Path) -> dict[str, SnapshotRecord]:
    manifest = inputs_dir / MANIFEST_NAME
    if not manifest.is_file():
        return {}
    try:
        loaded = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    records: dict[str, SnapshotRecord] = {}
    for name, entry in loaded.items():
        if not isinstance(entry, dict):
            continue
        try:
            records[name] = SnapshotRecord.parse(entry)
        except (TypeError, ValueError):
            # A damaged entry (e.g. an interrupted write) is dropped rather than crashing
            # resume; the input it describes is simply recollected as if never captured.
            continue
    return records


def _write_manifest(inputs_dir: Path, captured: list[SnapshotInput]) -> None:
    """Record provenance so a run can be traced back to the file it was launched with."""
    payload = {item.name: SnapshotRecord.of(item).as_payload() for item in captured}
    (inputs_dir / MANIFEST_NAME).write_text(yaml.dump(payload, sort_keys=False), encoding="utf-8")
