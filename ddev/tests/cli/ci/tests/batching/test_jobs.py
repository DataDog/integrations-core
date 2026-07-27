# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for expanding test units into concrete jobs.

A ``BatchJob`` is one ``target + environment + platform`` execution carrying job-level
``unit_tests``/``e2e_tests`` flags; it is never split into separate unit and E2E rows.
"""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.batching.jobs import expand_batch_jobs
from ddev.e2e.agent_images import UnknownPythonVersion
from ddev.utils.platform import PlatformName
from tests.helpers.batching import env, make_unit


def fake_resolver(python_version: str, platform: PlatformName) -> str:
    return f"agent:{python_version}-{platform}"


def test_single_environment_unit_becomes_one_job_with_facet_flags():
    # An environment enabled for both facets yields ONE job carrying both flags (no unit/E2E rows).
    units = [make_unit(name="postgres (py3.11)", environment=env("py3.11", unit=True, e2e=True))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert (job.name, job.target, job.environment) == ("postgres (py3.11)", "postgres", "py3.11")
    assert (job.unit_tests, job.e2e_tests) == (True, True)
    assert job.artifact_name() == "postgres_py3.11_linux"


def test_unit_only_environment_sets_only_unit_facet():
    units = [make_unit("redis", name="redis (py3.12)", environment=env("py3.12", unit=True, e2e=False))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert (job.unit_tests, job.e2e_tests) == (True, False)


def test_e2e_only_environment_sets_only_e2e_facet():
    units = [make_unit("redis", name="redis (py3.12)", environment=env("py3.12", unit=False, e2e=True))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert (job.unit_tests, job.e2e_tests) == (False, True)


def test_environmentless_target_emits_single_unit_job():
    [job] = expand_batch_jobs([make_unit("ddev", environment=env(""))], agent_image_resolver=fake_resolver)

    assert (job.name, job.target, job.environment) == ("ddev", "ddev", "")
    assert (job.unit_tests, job.e2e_tests) == (True, False)


def test_python_version_comes_from_the_environment():
    units = [make_unit(environment=env("py3.11", python_version="3.11"))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert job.python_version == "3.11"


def test_e2e_job_carries_the_resolved_agent_image():
    units = [make_unit(environment=env("py3.11", python_version="3.11", e2e=True))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert job.agent_image == "agent:3.11-linux"


def test_job_without_e2e_carries_no_agent_image():
    units = [make_unit(environment=env("py3.11", e2e=False))]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert job.agent_image is None


def test_unresolvable_agent_image_is_ignored_when_the_job_runs_no_e2e():
    # A Python version with no Agent image only breaks planning for jobs that would have used it.
    units = [make_unit(environment=env("py3.10", python_version="3.10", e2e=False))]

    [job] = expand_batch_jobs(units)

    assert job.agent_image is None


def test_unresolvable_agent_image_fails_planning_for_an_e2e_job():
    units = [make_unit(environment=env("py3.10", python_version="3.10", e2e=True))]

    with pytest.raises(UnknownPythonVersion, match="3.10"):
        expand_batch_jobs(units)


def test_runner_labels_and_platform_are_preserved():
    units = [
        make_unit(
            "sqlserver",
            name="sqlserver on Windows (py3.13)",
            platform=PlatformName.WINDOWS,
            runner_labels=("windows-2022", "x-large"),
            environment=env("py3.13", platform=PlatformName.WINDOWS),
        )
    ]

    [job] = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert job.runner_labels == ("windows-2022", "x-large")
    assert job.platform == PlatformName.WINDOWS


def test_multiple_units_expand_in_order_one_job_each():
    units = [
        make_unit(name="postgres (py3.11)", environment=env("py3.11")),
        make_unit(name="postgres (py3.12)", environment=env("py3.12")),
        make_unit("redis", name="redis (py3.11)", environment=env("py3.11")),
    ]

    jobs = expand_batch_jobs(units, agent_image_resolver=fake_resolver)

    assert [(j.name, j.environment) for j in jobs] == [
        ("postgres (py3.11)", "py3.11"),
        ("postgres (py3.12)", "py3.12"),
        ("redis (py3.11)", "py3.11"),
    ]
    assert len({j.artifact_name() for j in jobs}) == 3
