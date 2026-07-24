# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Expansion of test-planning units into concrete jobs.

A :class:`~ddev.cli.ci.tests.batching.units.TestUnit` is a planning unit; a
:class:`~ddev.cli.ci.tests.messages.BatchJob` is a concrete job the workflow runs. Per the
Dispatcher design, a job's logical identity is ``target + environment + platform``: every concrete
job carries exactly one resolved Hatch environment (or the empty selection for an environmentless
target) and is never duplicated into separate unit and E2E rows. Its ``unit_tests``/``e2e_tests``
flags describe which facets that single execution must produce, taken from the environment's
ddev-derived availability. A unit therefore expands into one job per resolved environment (or a
single environmentless job), preserving order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.cli.ci.tests.messages import BatchJob, Platform

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.batching.units import ResolvedEnvironment, TestUnit


def expand_batch_jobs(units: Sequence[TestUnit]) -> list[BatchJob]:
    """Expand ordered test units into ordered concrete jobs, preserving order.

    Each unit yields one job per resolved environment; a unit without environments yields a single
    unit/integration job with an empty environment selection.
    """
    jobs: list[BatchJob] = []
    for unit in units:
        platform = Platform(unit.platform)

        if not unit.environments:
            # Environmentless target (e.g. ddev): unit/integration tests with no environment.
            jobs.append(
                BatchJob(
                    name=unit.name,
                    target=unit.target,
                    runner_labels=unit.runner_labels,
                    environment="",
                    platform=platform,
                    unit_tests=True,
                    e2e_tests=False,
                )
            )
            continue

        for environment in unit.environments:
            jobs.append(
                BatchJob(
                    name=_job_name(unit, environment),
                    target=unit.target,
                    runner_labels=unit.runner_labels,
                    environment=environment.name,
                    platform=platform,
                    unit_tests=environment.test_available,
                    e2e_tests=environment.e2e_available,
                )
            )

    return jobs


def _job_name(unit: TestUnit, environment: ResolvedEnvironment) -> str:
    """Deterministic display name for one concrete job, unique within the plan.

    When environments are split each unit already covers a single environment and encodes it in
    its name, so the unit name is used directly. When environments are not split a unit covers
    several environments under one base name, so the environment is appended to keep every
    concrete job's display name (and thus its artifact identity) unique.
    """
    if len(unit.environments) == 1:
        return unit.name
    return f"{unit.name} ({environment.name})"
