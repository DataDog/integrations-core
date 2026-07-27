# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Builders for the Dispatcher batching planning tests."""

from __future__ import annotations

from ddev.cli.ci.tests.batching.git import ChangedFile, ChangeType
from ddev.cli.ci.tests.batching.units import ResolvedEnvironment, TestUnit

DEFAULT_PYTHON_VERSION = "3.13"
DEFAULT_RUNNER_LABELS = ("ubuntu-22.04",)


def env(
    name: str,
    platform: str = "linux",
    *,
    python_version: str = DEFAULT_PYTHON_VERSION,
    unit: bool = True,
    e2e: bool = False,
) -> ResolvedEnvironment:
    return ResolvedEnvironment(
        name=name,
        platform=platform,
        python_version=python_version,
        test_available=unit,
        e2e_available=e2e,
    )


def make_unit(
    target: str = "postgres",
    *,
    name: str | None = None,
    platform: str = "linux",
    runner_labels: tuple[str, ...] = DEFAULT_RUNNER_LABELS,
    environment: ResolvedEnvironment | None = None,
) -> TestUnit:
    return TestUnit(
        target=target,
        name=name if name is not None else target,
        platform=platform,
        runner_labels=runner_labels,
        environment=environment if environment is not None else env(target, platform),
    )


def modified(path: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.MODIFIED, path=path)


def renamed(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.RENAMED, path=destination, previous_path=source)


def copied(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.COPIED, path=destination, previous_path=source)
