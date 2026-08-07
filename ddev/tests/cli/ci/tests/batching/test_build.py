# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end tests for the public entry point, from changed files to ordered test units.

These use synthetic stand-ins for ddev's repository/registry/config and a synthetic
environment provider, so neither Git nor Hatch is ever invoked.
"""

from __future__ import annotations

import logging

import pytest

from ddev.cli.ci.tests.batching.build import (
    build_test_batches,
    build_test_units,
    create_test_batches,
    resolve_hatch_environments,
)
from ddev.cli.ci.tests.batching.exceptions import BatchValidationError, PlanningError
from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
from ddev.utils.platform import PlatformName
from tests.cli.ci.tests.helpers import DEFAULT_PYTHON_VERSION, FakeIntegration, FakeRegistry, env, jobs, modified


class FakeConfig:
    def __init__(self, ci=None):
        self._ci = ci or {}

    def get(self, pointer, default=None):
        prefix = "/overrides/ci/"
        if pointer.startswith(prefix):
            return self._ci.get(pointer[len(prefix) :], default)
        return default


class FakeRepo:
    def __init__(self, integrations, ci=None, name="core"):
        self.name = name
        self.integrations = FakeRegistry(integrations)
        self.config = FakeConfig(ci)


class FakeEnvironmentProvider:
    """Returns pre-configured resolved environments per integration; ignores the platforms hint."""

    def __init__(self, environments):
        self._environments = environments

    def __call__(self, integration, platforms):
        return list(self._environments.get(integration.name, []))


class EnvStub:
    """Minimal stand-in for ddev's Hatch ``Environment`` (no Hatch invocation)."""

    def __init__(self, name, *, test_env=True, e2e_env=False, platforms=(), python=None):
        self.name = name
        self.test_env = test_env
        self.e2e_env = e2e_env
        self.platforms = list(platforms)
        self.python = python


def test_build_end_to_end_direct_and_broad_overlap():
    repo = FakeRepo(
        [
            FakeIntegration("postgres"),
            FakeIntegration("mysql"),
            FakeIntegration("datadog_checks_base"),
        ]
    )
    provider = FakeEnvironmentProvider(
        {
            "postgres": [env("py3.11")],
            "mysql": [env("py3.11")],
            "datadog_checks_base": [env("py3.11")],
        }
    )
    changed = [
        modified("postgres/tests/test_a.py"),
        modified("datadog_checks_base/datadog_checks/base/utils/foo.py"),
    ]

    units = build_test_units(
        repo, changed, environment_provider=provider, default_python_version=DEFAULT_PYTHON_VERSION
    )

    # Broad rule adds the full eligible set; direct rule adds postgres; deduped and then ordered
    # by the display-order override (datadog_checks_base first, then alphabetical).
    assert [(u.target, u.name, u.environment.name) for u in units] == [
        ("datadog_checks_base", "datadog_checks_base (py3.11)", "py3.11"),
        ("mysql", "mysql (py3.11)", "py3.11"),
        ("postgres", "postgres (py3.11)", "py3.11"),
    ]


def test_build_warns_about_a_target_with_no_testable_environment(caplog):
    repo = FakeRepo([FakeIntegration("ddev")])
    provider = FakeEnvironmentProvider({})
    changed = [modified("ddev/src/ddev/foo.py")]

    with caplog.at_level(logging.WARNING, logger="ddev.cli.ci.tests.batching.build"):
        units = build_test_units(
            repo, changed, environment_provider=provider, default_python_version=DEFAULT_PYTHON_VERSION
        )

    assert len(units) == 1
    assert "ddev has a hatch.toml but no testable environment" in caplog.text


def test_build_does_not_warn_when_a_platform_alone_has_no_environments(caplog):
    # `disk` and friends run on Linux and Windows but declare only unconstrained environments, so
    # Windows legitimately falls back to an unnamed environment. That is not worth a warning.
    repo = FakeRepo([FakeIntegration("disk")], ci={"disk": {"platforms": ["linux", "windows"]}})
    provider = FakeEnvironmentProvider({"disk": [env("py3.13", platform=PlatformName.LINUX)]})
    changed = [modified("disk/tests/test_a.py")]

    with caplog.at_level(logging.WARNING, logger="ddev.cli.ci.tests.batching.build"):
        units = build_test_units(
            repo, changed, environment_provider=provider, default_python_version=DEFAULT_PYTHON_VERSION
        )

    # Both platforms are still planned; only the absence of a warning is under test here.
    assert len(units) == 2
    assert caplog.text == ""


def test_build_excludes_target_via_ci_override():
    repo = FakeRepo(
        [FakeIntegration("postgres"), FakeIntegration("hyperv")],
        ci={"hyperv": {"exclude": True}},
    )
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")], "hyperv": [env("py3.11")]})
    changed = [modified("postgres/tests/test_a.py"), modified("hyperv/tests/test_b.py")]

    units = build_test_units(
        repo, changed, environment_provider=provider, default_python_version=DEFAULT_PYTHON_VERSION
    )

    assert {u.target for u in units} == {"postgres"}


def test_build_applies_platform_and_runner_overrides():
    repo = FakeRepo(
        [FakeIntegration("sqlserver")],
        ci={"sqlserver": {"platforms": ["windows", "linux"], "runners": {"windows": ["windows-2022"]}}},
    )
    provider = FakeEnvironmentProvider(
        {"sqlserver": [env("py3.13", PlatformName.WINDOWS), env("py3.13", PlatformName.LINUX)]},
    )
    changed = [modified("sqlserver/tests/test_a.py")]

    units = build_test_units(
        repo, changed, environment_provider=provider, default_python_version=DEFAULT_PYTHON_VERSION
    )

    assert [(u.platform, u.runner_labels) for u in units] == [
        (PlatformName.WINDOWS, ("windows-2022",)),
        (PlatformName.LINUX, ("ubuntu-22.04",)),
    ]


def test_resolve_hatch_environments_includes_both_facets_and_excludes_neither():
    environments = [
        EnvStub("unit-only", test_env=True, e2e_env=False),
        EnvStub("e2e-only", test_env=False, e2e_env=True),
        EnvStub("both", test_env=True, e2e_env=True),
        EnvStub("neither", test_env=False, e2e_env=False),
    ]

    resolved = resolve_hatch_environments(
        environments, default_python_version=DEFAULT_PYTHON_VERSION, platforms=[PlatformName.LINUX]
    )

    assert [(r.name, r.test_available, r.e2e_available) for r in resolved] == [
        ("unit-only", True, False),
        ("e2e-only", False, True),
        ("both", True, True),
    ]


@pytest.mark.parametrize("python", ["3", "3.13t", "/usr/bin/python3.13", "three.thirteen"])
def test_resolve_hatch_environments_rejects_a_python_that_is_not_major_minor(python):
    # A unit-only environment never reaches the Agent image resolver, so this boundary is the only
    # place its version is checked.
    environments = [EnvStub("unit-only", test_env=True, e2e_env=False, python=python)]

    with pytest.raises(PlanningError, match="expected a `major.minor` version"):
        resolve_hatch_environments(
            environments, default_python_version=DEFAULT_PYTHON_VERSION, platforms=[PlatformName.LINUX]
        )


def test_resolve_hatch_environments_routes_constrained_platforms_without_crossing():
    # Mirrors sqlserver: os matrix surfaces as Environment.platforms via overrides.matrix.os.platforms.
    environments = [
        EnvStub("py3.13-linux", platforms=["linux", "macos"]),
        EnvStub("py3.13-windows", platforms=["windows"]),
    ]

    resolved = resolve_hatch_environments(
        environments,
        default_python_version=DEFAULT_PYTHON_VERSION,
        platforms=[PlatformName.WINDOWS, PlatformName.LINUX],
    )

    # Each environment lands only on its declared platform (intersected with the target's);
    # the Linux env never duplicates onto Windows and vice versa, and macos is dropped.
    assert [(r.name, r.platform) for r in resolved] == [
        ("py3.13-linux", PlatformName.LINUX),
        ("py3.13-windows", PlatformName.WINDOWS),
    ]


def test_resolve_hatch_environments_unconstrained_uses_single_default_platform():
    environments = [EnvStub("py3.11", platforms=[])]

    resolved = resolve_hatch_environments(
        environments,
        default_python_version=DEFAULT_PYTHON_VERSION,
        platforms=[PlatformName.LINUX, PlatformName.WINDOWS],
    )

    # No cross-product: an unconstrained env is routed only to the default (first) platform.
    assert [(r.name, r.platform) for r in resolved] == [("py3.11", PlatformName.LINUX)]


def test_resolve_hatch_environments_reads_the_python_version_from_hatch():
    environments = [EnvStub("py3.11-1.23", python="3.11")]

    resolved = resolve_hatch_environments(
        environments, default_python_version=DEFAULT_PYTHON_VERSION, platforms=[PlatformName.LINUX]
    )

    assert resolved[0].python_version == "3.11"


def test_resolve_hatch_environments_falls_back_when_hatch_declares_no_python():
    # Hatch omits `python` when the environment does not pin one; the name is not parsed as a
    # substitute because it only encodes the version by convention.
    environments = [EnvStub("py3.11-1.23", python=None)]

    resolved = resolve_hatch_environments(environments, default_python_version="3.9", platforms=[PlatformName.LINUX])

    assert resolved[0].python_version == "3.9"


def test_build_batches_end_to_end_split_defaults():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11", unit=True, e2e=True)]})
    changed = [modified("postgres/tests/test_a.py")]

    batches = build_test_batches(
        repo,
        changed,
        environment_provider=provider,
        config=BatchingConfig(),
        default_python_version=DEFAULT_PYTHON_VERSION,
    )

    assert len(batches) == 1
    batch = batches[0]
    assert batch.batch_id == "batch-01"
    assert batch.integrations == ["postgres"]
    # One job per target/environment/platform, carrying both facet flags for a both-enabled env.
    assert [(j.name, j.environment, j.unit_tests, j.e2e_tests) for j in batch.job_list] == [
        ("postgres (py3.11)", "py3.11", True, True),
    ]
    assert batch.jobs_count == 1


def test_build_batches_empty_input_returns_no_batches():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")]})
    changed = [modified("docs/readme.md")]

    assert (
        build_test_batches(
            repo,
            changed,
            environment_provider=provider,
            config=BatchingConfig(),
            default_python_version=DEFAULT_PYTHON_VERSION,
        )
        == []
    )


def test_build_batches_rejects_invalid_injected_strategy():
    repo = FakeRepo([FakeIntegration("postgres")])
    # Two environments expand to two jobs, so dropping one leaves a coverage gap.
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11"), env("py3.12")]})
    changed = [modified("postgres/tests/test_a.py")]

    def dropping_strategy(jobs, *, config):
        return [list(jobs[:-1])]  # loses the last job

    with pytest.raises(BatchValidationError, match="exactly once"):
        build_test_batches(
            repo,
            changed,
            environment_provider=provider,
            config=BatchingConfig(),
            default_python_version=DEFAULT_PYTHON_VERSION,
            strategy=dropping_strategy,
        )


def test_create_test_batches_numbers_and_populates_messages():
    groups = [jobs("postgres", 2), jobs("mysql", 1) + jobs("redis", 1)]

    batches = create_test_batches(groups)

    assert [b.batch_id for b in batches] == ["batch-01", "batch-02"]
    assert [b.id for b in batches] == ["batch-01", "batch-02"]
    assert [b.jobs_count for b in batches] == [2, 2]
    assert batches[0].integrations == ["postgres"]
    assert batches[1].integrations == ["mysql", "redis"]


def test_build_reads_supported_platforms_from_the_manifest():
    # Without a CI override, platforms come from the manifest's `Supported OS` classifier tags.
    repo = FakeRepo([FakeIntegration("hyperv", classifier_tags=["Supported OS::Windows"])])
    provider = FakeEnvironmentProvider({"hyperv": [env("py3.13", PlatformName.WINDOWS)]})
    changed = [modified("hyperv/tests/test_a.py")]

    units = build_test_units(
        repo, changed, environment_provider=provider, default_python_version=DEFAULT_PYTHON_VERSION
    )

    assert [u.platform for u in units] == [PlatformName.WINDOWS]


def test_build_only_expands_the_whole_repository_for_the_core_repo():
    # The repository-wide rule is gated on the repo name, so the same change outside core selects
    # only the directly modified target.
    integrations = [FakeIntegration("postgres"), FakeIntegration("datadog_checks_base")]
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")], "datadog_checks_base": [env("py3.11")]})
    changed = [modified("datadog_checks_base/datadog_checks/base/utils/foo.py")]

    def targets(repo):
        return {
            u.target
            for u in build_test_units(
                repo, changed, environment_provider=provider, default_python_version=DEFAULT_PYTHON_VERSION
            )
        }

    assert targets(FakeRepo(integrations)) == {"postgres", "datadog_checks_base"}
    assert targets(FakeRepo(integrations, name="extras")) == {"datadog_checks_base"}
