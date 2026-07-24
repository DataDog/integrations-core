# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end tests for the public entry point, from changed files to ordered test units.

These use synthetic stand-ins for ddev's repository/registry/config and a synthetic
environment provider, so neither Git nor Hatch is ever invoked.
"""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.batching.build import build_test_batches, build_test_units, resolve_hatch_environments
from ddev.cli.ci.tests.batching.exceptions import BatchValidationError, PlanningError
from ddev.cli.ci.tests.batching.git import ChangedFile, ChangeType
from ddev.cli.ci.tests.batching.units import ResolvedEnvironment
from ddev.cli.ci.tests.dispatcher_config import BatchingConfig


class FakeManifest:
    def __init__(self, classifier_tags):
        self._classifier_tags = list(classifier_tags)

    def get(self, pointer, default=None):
        if pointer == "/tile/classifier_tags":
            return list(self._classifier_tags)
        return default


class FakeIntegration:
    def __init__(self, name, *, is_testable=True, display_name=None, classifier_tags=()):
        self.name = name
        self.is_testable = is_testable
        self.display_name = display_name or name
        self.manifest = FakeManifest(classifier_tags)


class FakeRegistry:
    """Minimal stand-in for ddev's IntegrationRegistry (no git repository)."""

    def __init__(self, integrations):
        self._integrations = {integration.name: integration for integration in integrations}

    def get(self, name):
        try:
            return self._integrations[name]
        except KeyError:
            raise OSError(f"Integration does not exist: {name}") from None

    def iter_testable(self):
        return [integration for integration in self._integrations.values() if integration.is_testable]


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


def modified(path: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.MODIFIED, path=path)


def env(name: str, platform: str = "linux", *, unit: bool = True, e2e: bool = False) -> ResolvedEnvironment:
    return ResolvedEnvironment(name=name, platform=platform, test_available=unit, e2e_available=e2e)


class EnvStub:
    """Minimal stand-in for ddev's Hatch ``Environment`` (no Hatch invocation)."""

    def __init__(self, name, *, test_env=True, e2e_env=False, platforms=()):
        self.name = name
        self.test_env = test_env
        self.e2e_env = e2e_env
        self.platforms = list(platforms)


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

    units = build_test_units(repo, changed, environment_provider=provider)

    # Broad rule adds the full eligible set; direct rule adds postgres; deduped and then ordered
    # by the display-order override (datadog_checks_base first, then alphabetical).
    assert [(u.target, u.name, [e.name for e in u.environments]) for u in units] == [
        ("datadog_checks_base", "datadog_checks_base (py3.11)", ["py3.11"]),
        ("mysql", "mysql (py3.11)", ["py3.11"]),
        ("postgres", "postgres (py3.11)", ["py3.11"]),
    ]


def test_build_split_false_runs_all_environments_together():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11", e2e=False), env("py3.12", e2e=True)]})
    changed = [modified("postgres/tests/test_a.py")]

    units = build_test_units(repo, changed, environment_provider=provider, split_environments=False)

    assert len(units) == 1
    unit = units[0]
    assert unit.target == "postgres"
    assert [e.name for e in unit.environments] == ["py3.11", "py3.12"]
    assert [e.name for e in unit.environments if e.e2e_available] == ["py3.12"]


def test_build_environmentless_target():
    repo = FakeRepo([FakeIntegration("ddev")])
    provider = FakeEnvironmentProvider({})  # no environments for ddev
    changed = [modified("ddev/src/ddev/foo.py")]

    units = build_test_units(repo, changed, environment_provider=provider)

    assert len(units) == 1
    unit = units[0]
    assert (unit.target, unit.name, unit.platform, unit.environments) == ("ddev", "ddev", "linux", ())


def test_build_excludes_target_via_ci_override():
    repo = FakeRepo(
        [FakeIntegration("postgres"), FakeIntegration("hyperv")],
        ci={"hyperv": {"exclude": True}},
    )
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")], "hyperv": [env("py3.11")]})
    changed = [modified("postgres/tests/test_a.py"), modified("hyperv/tests/test_b.py")]

    units = build_test_units(repo, changed, environment_provider=provider)

    assert {u.target for u in units} == {"postgres"}


def test_build_applies_platform_and_runner_overrides():
    repo = FakeRepo(
        [FakeIntegration("sqlserver")],
        ci={"sqlserver": {"platforms": ["windows", "linux"], "runners": {"windows": ["windows-2022"]}}},
    )
    provider = FakeEnvironmentProvider(
        {"sqlserver": [env("py3.13", "windows"), env("py3.13", "linux")]},
    )
    changed = [modified("sqlserver/tests/test_a.py")]

    units = build_test_units(repo, changed, environment_provider=provider)

    assert [(u.platform, u.name, u.runner_labels) for u in units] == [
        ("windows", "sqlserver on Windows (py3.13)", ("windows-2022",)),
        ("linux", "sqlserver on Linux (py3.13)", ("ubuntu-22.04",)),
    ]


def test_resolve_hatch_environments_includes_both_facets_and_excludes_neither():
    environments = [
        EnvStub("unit-only", test_env=True, e2e_env=False),
        EnvStub("e2e-only", test_env=False, e2e_env=True),
        EnvStub("both", test_env=True, e2e_env=True),
        EnvStub("neither", test_env=False, e2e_env=False),
    ]

    resolved = resolve_hatch_environments(environments, ["linux"])

    assert [(r.name, r.test_available, r.e2e_available) for r in resolved] == [
        ("unit-only", True, False),
        ("e2e-only", False, True),
        ("both", True, True),
    ]


def test_resolve_hatch_environments_routes_constrained_platforms_without_crossing():
    # Mirrors sqlserver: os matrix surfaces as Environment.platforms via overrides.matrix.os.platforms.
    environments = [
        EnvStub("py3.13-linux", platforms=["linux", "macos"]),
        EnvStub("py3.13-windows", platforms=["windows"]),
    ]

    resolved = resolve_hatch_environments(environments, ["windows", "linux"])

    # Each environment lands only on its declared platform (intersected with the target's);
    # the Linux env never duplicates onto Windows and vice versa, and macos is dropped.
    assert [(r.name, r.platform) for r in resolved] == [
        ("py3.13-linux", "linux"),
        ("py3.13-windows", "windows"),
    ]


def test_resolve_hatch_environments_unconstrained_uses_single_default_platform():
    environments = [EnvStub("py3.11", platforms=[])]

    resolved = resolve_hatch_environments(environments, ["linux", "windows"])

    # No cross-product: an unconstrained env is routed only to the default (first) platform.
    assert [(r.name, r.platform) for r in resolved] == [("py3.11", "linux")]


def test_build_returns_nothing_for_irrelevant_changes():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")]})
    changed = [modified("docs/readme.md")]

    assert build_test_units(repo, changed, environment_provider=provider) == []


# ---------------------------------------------------------------------------
# build_test_batches
# ---------------------------------------------------------------------------


def test_build_batches_end_to_end_split_defaults():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11", unit=True, e2e=True)]})
    changed = [modified("postgres/tests/test_a.py")]

    batches = build_test_batches(repo, changed, environment_provider=provider, config=BatchingConfig())

    assert len(batches) == 1
    batch = batches[0]
    assert batch.batch_id == "batch-01"
    assert batch.integrations == ["postgres"]
    # One job per target/environment/platform, carrying both facet flags for a both-enabled env.
    assert [(j.name, j.environment, j.unit_tests, j.e2e_tests) for j in batch.job_list] == [
        ("postgres (py3.11)", "py3.11", True, True),
    ]
    assert batch.jobs_count == 1


def test_build_batches_emits_one_job_per_resolved_environment():
    # The authoritative job identity is exactly one (target, environment, platform) — there is no
    # representation for a single job spanning several environments and no batching-level knob to
    # collapse them. A target with two resolved environments therefore always produces two singular
    # jobs, in deterministic order, each carrying that environment's own facet flags.
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider(
        {"postgres": [env("py3.11", unit=True, e2e=False), env("py3.12", unit=True, e2e=True)]}
    )
    changed = [modified("postgres/tests/test_a.py")]

    batches = build_test_batches(repo, changed, environment_provider=provider, config=BatchingConfig())

    assert len(batches) == 1
    # Each concrete job carries exactly one real environment, never a joined label.
    assert [(j.name, j.environment, j.unit_tests, j.e2e_tests) for j in batches[0].job_list] == [
        ("postgres (py3.11)", "py3.11", True, False),
        ("postgres (py3.12)", "py3.12", True, True),
    ]


def test_build_batches_empty_input_returns_no_batches():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")]})
    changed = [modified("docs/readme.md")]

    assert build_test_batches(repo, changed, environment_provider=provider, config=BatchingConfig()) == []


def test_build_batches_rejects_invalid_injected_strategy():
    repo = FakeRepo([FakeIntegration("postgres")])
    # Two environments expand to two jobs, so dropping one leaves a coverage gap.
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11"), env("py3.12")]})
    changed = [modified("postgres/tests/test_a.py")]

    def dropping_strategy(jobs, *, capacity, config):
        return [list(jobs[:-1])]  # loses the last job

    with pytest.raises(BatchValidationError, match="exactly once"):
        build_test_batches(
            repo, changed, environment_provider=provider, config=BatchingConfig(), strategy=dropping_strategy
        )


def test_build_batches_oversized_integration_fails_when_splitting_disabled():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11"), env("py3.12")]})
    changed = [modified("postgres/tests/test_a.py")]
    # Two unit jobs (one per environment) for one integration, capacity 1, splitting disabled.
    config = BatchingConfig(max_jobs_per_batch=1, allow_integration_splitting=False)

    with pytest.raises(PlanningError, match="exceeding the batch capacity"):
        build_test_batches(repo, changed, environment_provider=provider, config=config)


def test_build_batches_numbering_is_deterministic_across_calls():
    repo = FakeRepo([FakeIntegration("postgres"), FakeIntegration("mysql")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")], "mysql": [env("py3.11")]})
    changed = [modified("postgres/tests/test_a.py"), modified("mysql/tests/test_b.py")]
    config = BatchingConfig(max_jobs_per_batch=1)

    first = [b.batch_id for b in build_test_batches(repo, changed, environment_provider=provider, config=config)]
    second = [b.batch_id for b in build_test_batches(repo, changed, environment_provider=provider, config=config)]

    assert first == second == ["batch-01", "batch-02"]
