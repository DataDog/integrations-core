# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for expanding test units into concrete jobs.

A ``BatchJob`` is one ``target + environment + platform`` execution carrying job-level
``unit_tests``/``e2e_tests`` flags; it is never split into separate unit and E2E rows.
"""

from __future__ import annotations

from ddev.cli.ci.tests.batching.jobs import expand_batch_jobs
from ddev.cli.ci.tests.batching.units import ResolvedEnvironment, TestUnit
from ddev.cli.ci.tests.messages import Platform


def unit(
    name: str,
    *,
    target: str = "postgres",
    platform: str = "linux",
    runner_labels: tuple[str, ...] = ("ubuntu-22.04",),
    environments: tuple[ResolvedEnvironment, ...] = (),
) -> TestUnit:
    return TestUnit(
        target=target,
        name=name,
        platform=platform,
        runner_labels=runner_labels,
        environments=environments,
    )


def env(name: str, *, unit: bool = True, e2e: bool = False, platform: str = "linux") -> ResolvedEnvironment:
    return ResolvedEnvironment(name=name, platform=platform, test_available=unit, e2e_available=e2e)


def test_single_environment_unit_becomes_one_job_with_facet_flags():
    # An environment enabled for both facets yields ONE job carrying both flags (no unit/E2E rows).
    units = [unit("postgres (py3.11)", environments=(env("py3.11", unit=True, e2e=True),))]

    jobs = expand_batch_jobs(units)

    assert len(jobs) == 1
    job = jobs[0]
    assert (job.name, job.target, job.environment) == ("postgres (py3.11)", "postgres", "py3.11")
    assert (job.unit_tests, job.e2e_tests) == (True, True)
    assert job.artifact_name() == "postgres_py3.11_linux"


def test_unit_only_environment_sets_only_unit_facet():
    units = [unit("redis (py3.12)", target="redis", environments=(env("py3.12", unit=True, e2e=False),))]

    [job] = expand_batch_jobs(units)

    assert (job.unit_tests, job.e2e_tests) == (True, False)


def test_e2e_only_environment_sets_only_e2e_facet():
    units = [unit("redis (py3.12)", target="redis", environments=(env("py3.12", unit=False, e2e=True),))]

    [job] = expand_batch_jobs(units)

    assert (job.unit_tests, job.e2e_tests) == (False, True)


def test_unsplit_unit_expands_to_one_job_per_real_environment():
    # A unit covering several environments (as build_test_units can produce at the unit layer)
    # expands into one job per resolved environment, each carrying a single real environment and
    # its own facet flags — never a job spanning multiple environments.
    units = [
        unit(
            "postgres",
            environments=(
                env("py3.11", unit=True, e2e=False),
                env("py3.12", unit=True, e2e=True),
                env("py3.13", unit=False, e2e=True),
            ),
        )
    ]

    jobs = expand_batch_jobs(units)

    assert [(j.name, j.environment, j.unit_tests, j.e2e_tests) for j in jobs] == [
        ("postgres (py3.11)", "py3.11", True, False),
        ("postgres (py3.12)", "py3.12", True, True),
        ("postgres (py3.13)", "py3.13", False, True),
    ]
    # Each job's environment is a single real environment and artifact identities stay unique.
    assert [j.artifact_name() for j in jobs] == [
        "postgres_py3.11_linux",
        "postgres_py3.12_linux",
        "postgres_py3.13_linux",
    ]
    assert len({j.artifact_name() for j in jobs}) == 3


def test_environmentless_target_emits_single_unit_job():
    [job] = expand_batch_jobs([unit("ddev", target="ddev", environments=())])

    assert (job.name, job.target, job.environment) == ("ddev", "ddev", "")
    assert (job.unit_tests, job.e2e_tests) == (True, False)


def test_runner_labels_and_platform_are_preserved():
    units = [
        unit(
            "sqlserver on Windows (py3.13)",
            target="sqlserver",
            platform="windows",
            runner_labels=("windows-2022", "x-large"),
            environments=(env("py3.13", platform="windows"),),
        )
    ]

    [job] = expand_batch_jobs(units)

    assert job.runner_labels == ("windows-2022", "x-large")
    assert job.platform == Platform.WINDOWS


def test_multiple_units_expand_in_order_one_job_each():
    units = [
        unit("postgres (py3.11)", environments=(env("py3.11"),)),
        unit("postgres (py3.12)", environments=(env("py3.12"),)),
        unit("redis (py3.11)", target="redis", environments=(env("py3.11"),)),
    ]

    jobs = expand_batch_jobs(units)

    assert [(j.name, j.environment) for j in jobs] == [
        ("postgres (py3.11)", "py3.11"),
        ("postgres (py3.12)", "py3.12"),
        ("redis (py3.11)", "py3.11"),
    ]
