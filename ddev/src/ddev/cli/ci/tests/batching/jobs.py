# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Expansion of test-planning units into concrete jobs.

A :class:`~ddev.cli.ci.tests.batching.units.TestUnit` is a planning unit; a
:class:`~ddev.cli.ci.tests.messages.BatchJob` is a concrete job the workflow runs. Per the
Dispatcher design, a job's logical identity is ``target + environment + platform``: every concrete
job carries exactly one resolved Hatch environment (empty for an environmentless target) and is
never duplicated into separate unit and E2E rows. Its ``unit_tests``/``e2e_tests`` flags describe
which facets that single execution must produce, taken from the environment's ddev-derived
availability.

Each job also carries the Python version the runner must set up and, when it runs E2E tests, the
Agent image to run them against. Resolving the image here rather than in the workflow keeps the
plan self-describing: the recorded plan states exactly what every job ran against.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from ddev.cli.ci.tests.messages import BatchJob, Platform
from ddev.e2e.agent_images import get_agent_image

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.batching.units import TestUnit


class AgentImageResolver(Protocol):
    """Resolves the E2E Agent image for a Python version on a platform."""

    def __call__(self, python_version: str, platform: str) -> str: ...


def expand_batch_jobs(
    units: Sequence[TestUnit],
    *,
    agent_image_resolver: AgentImageResolver = get_agent_image,
) -> list[BatchJob]:
    """Expand ordered test units into ordered concrete jobs, one per unit, preserving order.

    A job that runs no E2E facet gets no Agent image, so an unresolvable image can only ever fail
    a plan that would actually have used it.
    """
    jobs: list[BatchJob] = []
    for unit in units:
        environment = unit.environment
        jobs.append(
            BatchJob(
                name=unit.name,
                target=unit.target,
                runner_labels=unit.runner_labels,
                environment=environment.name,
                platform=Platform(unit.platform),
                python_version=environment.python_version,
                unit_tests=environment.test_available,
                e2e_tests=environment.e2e_available,
                agent_image=(
                    agent_image_resolver(environment.python_version, unit.platform)
                    if environment.e2e_available
                    else None
                ),
            )
        )

    return jobs
