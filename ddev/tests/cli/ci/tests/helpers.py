# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Builders for the Dispatcher batching planning tests."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence

from ddev.cli.ci.tests.batching.units import ResolvedEnvironment, TestUnit
from ddev.cli.ci.tests.messages import BatchJob
from ddev.event_bus.orchestrator import BaseMessage
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


def make_job(
    name: str = "job-1",
    *,
    target: str = "ntp",
    environment: str = "py3.13",
    platform: PlatformName = PlatformName.LINUX,
    python_version: str = DEFAULT_PYTHON_VERSION,
    runner_labels: tuple[str, ...] = DEFAULT_RUNNER_LABELS,
    unit_tests: bool = True,
    e2e_tests: bool = False,
    agent_image: str | None = None,
) -> BatchJob:
    return BatchJob(
        name=name,
        target=target,
        runner_labels=runner_labels,
        environment=environment,
        platform=platform,
        python_version=python_version,
        unit_tests=unit_tests,
        e2e_tests=e2e_tests,
        agent_image=agent_image,
    )


def jobs(target: str, count: int) -> list[BatchJob]:
    # Each job carries a distinct environment, as production jobs within an integration do, so
    # names and artifact identities are unique within the target.
    return [make_job(f"{target}-{index}", target=target, environment=f"env-{index}") for index in range(count)]


class FakeManifest:
    def __init__(self, classifier_tags: Sequence[str] = ()):
        self._classifier_tags = list(classifier_tags)

    def get(self, pointer, default=None):
        if pointer == "/tile/classifier_tags":
            return list(self._classifier_tags)
        return default


class FakeIntegration:
    def __init__(
        self,
        name: str,
        *,
        is_testable: bool = True,
        display_name: str | None = None,
        classifier_tags: Sequence[str] = (),
    ):
        self.name = name
        self.is_testable = is_testable
        self.display_name = display_name or name
        self.manifest = FakeManifest(classifier_tags)


class FakeRegistry:
    """Stand-in for ddev's IntegrationRegistry; `get` raises OSError for an unknown name."""

    def __init__(self, integrations: Sequence[FakeIntegration], *, changed: Sequence[str] = ()):
        self._integrations = {integration.name: integration for integration in integrations}
        self._changed = set(changed)

    def get(self, name: str) -> FakeIntegration:
        try:
            return self._integrations[name]
        except KeyError:
            raise OSError(f"Integration does not exist: {name}") from None

    def iter_testable(self, selection: Iterable[str] = ()) -> list[FakeIntegration]:
        # ddev's registry resolves an empty selection to `changed`, so only `all` sees everything
        candidates = (
            self._integrations.values()
            if "all" in selection
            else [integration for integration in self._integrations.values() if integration.name in self._changed]
        )
        return [integration for integration in candidates if integration.is_testable]


def modified(path: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.MODIFIED, path=path)


def renamed(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.RENAMED, path=destination, previous_path=source)


def copied(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.COPIED, path=destination, previous_path=source)


def drain_queue(queue: asyncio.Queue[BaseMessage]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    while not queue.empty():
        messages.append(queue.get_nowait())
    return messages
