# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""End-to-end tests for the public entry point, from changed files to ordered test units.

These use synthetic stand-ins for ddev's repository/registry/config and a synthetic
environment provider, so neither Git nor Hatch is ever invoked.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import pytest

from ddev.cli.ci.tests.batching.build import (
    build_test_batches as _build_test_batches,
)
from ddev.cli.ci.tests.batching.build import (
    build_test_units as _build_test_units,
)
from ddev.cli.ci.tests.batching.build import (
    create_test_batches,
    supports_minimum_base_package,
)
from ddev.cli.ci.tests.batching.exceptions import BatchValidationError
from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
from ddev.utils.platform import PlatformName

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.batching.units import ResolvedEnvironment
    from ddev.cli.ci.tests.messages import BatchJob
from tests.cli.ci.tests.helpers import FakeIntegration, FakeRegistry, env, jobs, modified
from tests.helpers.monitoring import RecordingJsonHandler, make_monitor

build_test_units = partial(_build_test_units, monitor=make_monitor('planner'))
build_test_batches = partial(_build_test_batches, monitor=make_monitor('planner'))


class FakeConfig:
    def __init__(self, ci: dict[str, dict] | None = None):
        self._ci = ci or {}

    def get(self, pointer: str, default: object = None) -> object:
        prefix = "/overrides/ci/"
        if pointer.startswith(prefix):
            return self._ci.get(pointer[len(prefix) :], default)
        return default


class FakeRepo:
    def __init__(
        self,
        integrations: Sequence[FakeIntegration],
        ci: dict[str, dict] | None = None,
        name: str = "core",
    ):
        self.name = name
        self.integrations = FakeRegistry(integrations)
        self.config = FakeConfig(ci)


class FakeEnvironmentProvider:
    """Returns pre-configured resolved environments per integration; ignores the platforms hint."""

    def __init__(self, environments: dict[str, list[ResolvedEnvironment]]):
        self._environments = environments

    def __call__(self, integration: FakeIntegration, platforms: Sequence[PlatformName]) -> list[ResolvedEnvironment]:
        return list(self._environments.get(integration.name, []))


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
    assert [(u.target, u.name, u.environment.name) for u in units] == [
        ("datadog_checks_base", "datadog_checks_base (py3.11)", "py3.11"),
        ("mysql", "mysql (py3.11)", "py3.11"),
        ("postgres", "postgres (py3.11)", "py3.11"),
    ]


def test_build_warns_about_a_target_with_no_testable_environment():
    repo = FakeRepo([FakeIntegration("ddev")])
    provider = FakeEnvironmentProvider({})
    changed = [modified("ddev/src/ddev/foo.py")]
    handler = RecordingJsonHandler()

    units = build_test_units(
        repo,
        changed,
        environment_provider=provider,
        monitor=make_monitor('planner', handler=handler),
    )

    # The target is dropped rather than planned with an invented environment.
    assert units == []
    [event] = handler.events
    assert event['event'] == "ddev has a hatch.toml but no testable environment"


def test_build_plans_nothing_for_a_platform_whose_environments_are_constrained_elsewhere():
    # A target declaring a platform that every environment is constrained away from is a weaker
    # version of the same contradiction: odd configuration, worth surfacing, not worth failing.
    repo = FakeRepo([FakeIntegration("disk")], ci={"disk": {"platforms": ["linux", "windows"]}})
    provider = FakeEnvironmentProvider({"disk": [env("py3.13", platform=PlatformName.LINUX)]})
    changed = [modified("disk/tests/test_a.py")]
    handler = RecordingJsonHandler()

    units = build_test_units(
        repo,
        changed,
        environment_provider=provider,
        monitor=make_monitor('planner', handler=handler),
    )

    assert [unit.platform for unit in units] == [PlatformName.LINUX]
    [event] = handler.events
    assert event['event'] == "disk runs on windows but no environment tests it"


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
        {"sqlserver": [env("py3.13", PlatformName.WINDOWS), env("py3.13", PlatformName.LINUX)]},
    )
    changed = [modified("sqlserver/tests/test_a.py")]

    units = build_test_units(repo, changed, environment_provider=provider)

    assert [(u.platform, u.runner_labels) for u in units] == [
        (PlatformName.WINDOWS, ("windows-2022",)),
        (PlatformName.LINUX, ("ubuntu-22.04",)),
    ]


def test_build_batches_end_to_end_split_defaults():
    repo = FakeRepo([FakeIntegration("postgres")])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11", unit=True, e2e=True)]})
    changed = [modified("postgres/tests/test_a.py")]

    batches = build_test_batches(
        repo,
        changed,
        environment_provider=provider,
        config=BatchingConfig(),
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


@pytest.mark.parametrize(
    ("attributes", "supported"),
    [
        pytest.param({}, True, id="shipped-integration-pinning-a-base-package-version"),
        # The tooling targets are `is-integration = false` in the repository configuration.
        pytest.param({"is_integration": False}, False, id="tooling-target"),
        pytest.param({"is_package": False}, False, id="tile-without-a-package"),
        # `lparstats` depends on `datadog-checks-base` without a specifier.
        pytest.param({"minimum_base_package_version": None}, False, id="base-package-not-pinned"),
    ],
)
def test_supports_minimum_base_package_matches_what_compat_pins(attributes: dict, supported: bool):
    assert supports_minimum_base_package(FakeIntegration("postgres", **attributes)) is supported


def test_build_batches_plans_minimum_base_package_replicas():
    repo = FakeRepo([FakeIntegration("postgres"), FakeIntegration("ddev", is_integration=False)])
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11", unit=True, e2e=True)], "ddev": [env("py3.11")]})
    changed = [modified("postgres/tests/test_a.py"), modified("ddev/tests/test_b.py")]

    [batch] = build_test_batches(
        repo,
        changed,
        environment_provider=provider,
        config=BatchingConfig(),
        minimum_base_package=True,
    )

    assert [(j.name, j.minimum_base_package) for j in batch.job_list] == [
        ("ddev (py3.11)", False),
        ("postgres (py3.11)", False),
        ("postgres (MBP) (py3.11)", True),
    ]
    assert batch.jobs_count == 3


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
        )
        == []
    )


def test_build_batches_rejects_invalid_injected_strategy():
    repo = FakeRepo([FakeIntegration("postgres")])
    # Two environments expand to two jobs, so dropping one leaves a coverage gap.
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11"), env("py3.12")]})
    changed = [modified("postgres/tests/test_a.py")]

    def dropping_strategy(jobs: Sequence[BatchJob], *, config: BatchingConfig) -> list[list[BatchJob]]:
        return [list(jobs[:-1])]  # loses the last job

    with pytest.raises(BatchValidationError, match="exactly once"):
        build_test_batches(
            repo,
            changed,
            environment_provider=provider,
            config=BatchingConfig(),
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

    units = build_test_units(repo, changed, environment_provider=provider)

    assert [u.platform for u in units] == [PlatformName.WINDOWS]


def test_build_ignores_manifest_platforms_ddev_cannot_test():
    # `ibm_mq` and friends advertise AIX. It has no runner, so it must be ignored rather than
    # failing the plan for every target the run selected.
    repo = FakeRepo(
        [FakeIntegration("ibm_mq", classifier_tags=["Supported OS::Linux", "Supported OS::AIX"])],
    )
    provider = FakeEnvironmentProvider({"ibm_mq": [env("py3.13")]})
    changed = [modified("ibm_mq/tests/test_a.py")]

    units = build_test_units(repo, changed, environment_provider=provider)

    assert [u.platform for u in units] == [PlatformName.LINUX]


def test_build_only_expands_the_whole_repository_for_the_core_repo():
    # The repository-wide rule is gated on the repo name, so the same change outside core selects
    # only the directly modified target.
    integrations = [FakeIntegration("postgres"), FakeIntegration("datadog_checks_base")]
    provider = FakeEnvironmentProvider({"postgres": [env("py3.11")], "datadog_checks_base": [env("py3.11")]})
    changed = [modified("datadog_checks_base/datadog_checks/base/utils/foo.py")]

    def targets(repo: FakeRepo) -> set[str]:
        return {u.target for u in build_test_units(repo, changed, environment_provider=provider)}

    assert targets(FakeRepo(integrations)) == {"postgres", "datadog_checks_base"}
    assert targets(FakeRepo(integrations, name="extras")) == {"datadog_checks_base"}
