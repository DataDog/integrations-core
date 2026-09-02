# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Expansion of test units into the concrete jobs a workflow runs."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Protocol

from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.cli.ci.tests.messages import MINIMUM_BASE_PACKAGE_PREFIX, BatchJob
from ddev.e2e.agent_images import AgentImageError, get_agent_image

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.batching.units import TestUnit
    from ddev.utils.platform import PlatformName


class AgentImageResolver(Protocol):
    """Resolves the E2E Agent image for a Python version on a platform."""

    def __call__(self, python_version: str, platform: PlatformName) -> str: ...


def expand_batch_jobs(
    units: Sequence[TestUnit],
    *,
    agent_image_resolver: AgentImageResolver = get_agent_image,
    minimum_base_package: bool = False,
) -> list[BatchJob]:
    """Expand test units into concrete jobs, one per unit, preserving order.

    The Agent image is resolved here rather than in the workflow so the recorded plan states what
    every job ran against. A job with no E2E tests gets no image, so an unresolvable one can only
    fail a plan that would actually have used it.

    With *minimum_base_package*, each unit also yields a replica pinned to the oldest supported base
    package, so a run that wants that coverage plans it instead of the workflow making a second pass.
    """
    jobs: list[BatchJob] = []
    for unit in units:
        environment = unit.environment
        job = BatchJob(
            name=unit.name,
            target=unit.target,
            runner_labels=unit.runner_labels,
            environment=environment.name,
            platform=unit.platform,
            python_version=environment.python_version,
            unit_tests=environment.test_available,
            e2e_tests=environment.e2e_available,
            agent_image=_resolve_agent_image(unit, agent_image_resolver),
        )
        jobs.append(job)
        if minimum_base_package and (replica := _minimum_base_package_replica(job)) is not None:
            jobs.append(replica)

    return jobs


def _minimum_base_package_replica(job: BatchJob) -> BatchJob | None:
    """The minimum-base-package variant of *job*, or `None` when there is nothing for it to run.

    The variant only substitutes the base package the unit tests import, so it runs no E2E tests and
    needs no Agent image. It also runs without coverage, because measuring an old base package says
    nothing about the coverage of the code under test. A unit-less job would therefore have no work
    left at all, so none is planned.
    """
    if not job.unit_tests:
        return None

    return dataclasses.replace(
        job,
        name=f"{MINIMUM_BASE_PACKAGE_PREFIX}{job.name}",
        e2e_tests=False,
        agent_image=None,
        minimum_base_package=True,
        coverage=False,
    )


def _resolve_agent_image(unit: TestUnit, resolver: AgentImageResolver) -> str | None:
    """Resolve one unit's Agent image, reporting a failure as a planning failure.

    The resolver raises its own Agent-image exceptions, which say nothing about which job asked.
    They are translated here rather than at their source so `ddev.e2e` stays independent of the
    planner.
    """
    if not unit.environment.e2e_available:
        return None

    try:
        return resolver(unit.environment.python_version, unit.platform)
    except AgentImageError as e:
        raise PlanningError(f"{unit.name!r} needs an E2E Agent image but none resolves: {e}") from e
