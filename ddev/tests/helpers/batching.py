# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Builders for the Dispatcher batching planning tests."""

from __future__ import annotations

from ddev.cli.ci.tests.batching.units import ResolvedEnvironment, TestUnit
from ddev.cli.ci.tests.messages import BatchJob
from ddev.utils.git import ChangedFile, ChangeType
from ddev.utils.platform import PlatformName

DEFAULT_PYTHON_VERSION = "3.13"
DEFAULT_RUNNER_LABELS = ("ubuntu-22.04",)


def env(
    name: str,
    platform: PlatformName = PlatformName.LINUX,
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
    platform: PlatformName = PlatformName.LINUX,
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


def jobs(target: str, count: int) -> list[BatchJob]:
    # Each job carries a distinct environment, as production jobs within an integration do, so
    # names and artifact identities are unique within the target.
    return [
        BatchJob(
            name=f"{target}-{index}",
            target=target,
            runner_labels=DEFAULT_RUNNER_LABELS,
            environment=f"env-{index}",
            platform=PlatformName.LINUX,
            python_version=DEFAULT_PYTHON_VERSION,
            unit_tests=True,
            e2e_tests=False,
        )
        for index in range(count)
    ]


def modified(path: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.MODIFIED, path=path)


def renamed(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.RENAMED, path=destination, previous_path=source)


def copied(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.COPIED, path=destination, previous_path=source)
