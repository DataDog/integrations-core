# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for expanding test units into concrete jobs."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.cli.ci.tests.batching.jobs import expand_batch_jobs
from ddev.e2e.agent_images import UnknownPythonVersion
from ddev.utils.platform import PlatformName
from tests.cli.ci.tests.helpers import env, make_unit


def fake_resolver(python_version: str, platform: PlatformName) -> str:
    return f"agent:{python_version}-{platform}"


@pytest.mark.parametrize(
    ("environment_name", "unit", "e2e"),
    [
        pytest.param("py3.11", True, True, id="both-facets-stay-one-job"),
        pytest.param("py3.12", True, False, id="unit-only"),
        pytest.param("py3.12", False, True, id="e2e-only"),
        pytest.param("", True, False, id="environmentless"),
    ],
)
def test_each_environment_becomes_one_job_carrying_its_facets(environment_name, unit, e2e):
    units = [make_unit(environment=env(environment_name, unit=unit, e2e=e2e))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert (job.environment, job.unit_tests, job.e2e_tests) == (environment_name, unit, e2e)


def test_e2e_job_carries_the_resolved_agent_image():
    units = [make_unit(environment=env("py3.11", python_version="3.11", e2e=True))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert job.agent_image == "agent:3.11-linux"


def test_unresolvable_agent_image_is_ignored_when_the_job_runs_no_e2e():
    # A Python version with no Agent image only breaks planning for jobs that would have used it.
    units = [make_unit(environment=env("py3.10", python_version="3.10", e2e=False))]

    [job] = expand_batch_jobs(units)

    assert job.agent_image is None


def test_unresolvable_agent_image_fails_planning_for_an_e2e_job():
    units = [make_unit(environment=env("py3.10", python_version="3.10", e2e=True))]

    # Reported as a planning failure naming the job, since the Agent-image error alone says only
    # that some 3.10 was asked for
    with pytest.raises(PlanningError, match="needs an E2E Agent image") as failure:
        expand_batch_jobs(units)

    assert units[0].name in str(failure.value)
    assert isinstance(failure.value.__cause__, UnknownPythonVersion)


def test_runner_labels_and_platform_are_preserved():
    units = [
        make_unit(
            "sqlserver",
            platform=PlatformName.WINDOWS,
            runner_labels=("windows-2022", "x-large"),
            environment=env("py3.13", platform=PlatformName.WINDOWS),
        )
    ]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert (job.runner_labels, job.platform) == (("windows-2022", "x-large"), PlatformName.WINDOWS)


def test_minimum_base_package_replica_is_planned_alongside_the_job():
    units = [make_unit("postgres", name="postgres (py3.13)", environment=env("py3.13", unit=True, e2e=True))]

    jobs = expand_batch_jobs(units, agent_image_resolver=fake_resolver, minimum_base_package=True)

    original, replica = jobs
    # The replica substitutes the base package the unit tests import, so it runs unit tests only and
    # needs no Agent image. Distinct name and artifact identity are what keep the pair's workflow
    # correlation and downloaded artifacts from collapsing onto each other.
    assert (replica.unit_tests, replica.e2e_tests, replica.agent_image) == (True, False, None)
    assert replica.minimum_base_package and not replica.coverage
    assert replica.name != original.name
    assert replica.artifact_name() != original.artifact_name()


def test_jobs_are_not_replicated_by_default():
    # A run that does not ask for it pays nothing: testing against a given Agent image, for one, has
    # a single base package version available and so has no second variant to run.
    units = [make_unit(environment=env("py3.13"))]

    jobs = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert [job.minimum_base_package for job in jobs] == [False]


def test_no_replica_for_a_job_that_runs_no_unit_tests():
    # Only unit tests import the base package, so an E2E-only job's replica would run nothing.
    units = [make_unit(environment=env("py3.13", unit=False, e2e=True))]

    jobs = expand_batch_jobs(units, agent_image_resolver=fake_resolver, minimum_base_package=True)

    assert len(jobs) == 1


def test_no_replica_for_a_target_that_does_not_support_it():
    # `ddev test --compat` only pins the base package for a shipped integration that declares a
    # version, so replicating anything else (`ddev`, `datadog_checks_base`) reruns the same suite.
    units = [make_unit("ddev", environment=env("py3.13"), supports_minimum_base_package=False)]

    jobs = expand_batch_jobs(units, agent_image_resolver=fake_resolver, minimum_base_package=True)

    assert len(jobs) == 1
    assert not jobs[0].minimum_base_package


def test_only_supporting_targets_are_replicated_in_a_mixed_plan():
    units = [
        make_unit("postgres", name="postgres", environment=env("py3.13")),
        make_unit("ddev", name="ddev", environment=env("py3.13"), supports_minimum_base_package=False),
    ]

    jobs = expand_batch_jobs(units, agent_image_resolver=fake_resolver, minimum_base_package=True)

    assert [(job.target, job.minimum_base_package) for job in jobs] == [
        ("postgres", False),
        ("postgres", True),
        ("ddev", False),
    ]


def test_multiple_units_expand_in_order_one_job_each():
    units = [
        make_unit(name="postgres (py3.11)", environment=env("py3.11")),
        make_unit(name="postgres (py3.12)", environment=env("py3.12")),
        make_unit("redis", name="redis (py3.11)", environment=env("py3.11")),
    ]

    jobs = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert [(j.name, j.target, j.environment) for j in jobs] == [
        ("postgres (py3.11)", "postgres", "py3.11"),
        ("postgres (py3.12)", "postgres", "py3.12"),
        ("redis (py3.11)", "redis", "py3.11"),
    ]
