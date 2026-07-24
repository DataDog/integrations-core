# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.ci.tests.batching.units import (
    ResolvedEnvironment,
    TargetDefinition,
    TestUnit,
    expand_test_units,
    normalize_job_name,
    resolve_platforms,
)


def env(name: str, platform: str = "linux", *, unit: bool = True, e2e: bool = False) -> ResolvedEnvironment:
    return ResolvedEnvironment(name=name, platform=platform, test_available=unit, e2e_available=e2e)


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param('foo/bar:baz', 'foo_bar_baz', id="reserved-replaced"),
        pytest.param('My Integration', 'My Integration', id="allowed-unchanged"),
    ],
)
def test_normalize_job_name(raw, expected):
    assert normalize_job_name(raw) == expected


@pytest.mark.parametrize(
    "platform_override, supported_os, expected",
    [
        pytest.param(["linux", "windows"], ["Windows"], ["linux", "windows"], id="override-wins"),
        pytest.param([], ["Windows"], ["windows"], id="windows-exclusive"),
        pytest.param([], ["Linux", "Windows"], ["linux"], id="multi-os-defaults-linux"),
        pytest.param([], [], ["linux"], id="no-info-defaults-linux"),
    ],
)
def test_resolve_platforms(platform_override, supported_os, expected):
    assert resolve_platforms(platform_override, supported_os) == expected


def test_expand_splits_each_environment_into_its_own_unit():
    targets = [
        TargetDefinition("postgres", environments=(env("py3.11", e2e=True), env("py3.12", e2e=True))),
    ]

    units = expand_test_units(targets, split_environments=True)

    assert units == [
        TestUnit(
            target="postgres",
            name="postgres (py3.11)",
            platform="linux",
            runner_labels=("ubuntu-22.04",),
            environments=(env("py3.11", e2e=True),),
        ),
        TestUnit(
            target="postgres",
            name="postgres (py3.12)",
            platform="linux",
            runner_labels=("ubuntu-22.04",),
            environments=(env("py3.12", e2e=True),),
        ),
    ]


def test_expand_preserves_environment_order():
    targets = [
        TargetDefinition(
            "postgres",
            environments=(env("py3.11-9"), env("py3.11-10"), env("py3.12-9"), env("py3.12-10")),
        ),
    ]

    units = expand_test_units(targets, split_environments=True)

    assert [u.environments[0].name for u in units] == ["py3.11-9", "py3.11-10", "py3.12-9", "py3.12-10"]


def test_expand_environmentless_target_has_empty_selection():
    targets = [TargetDefinition("postgres")]

    units = expand_test_units(targets)

    assert units == [
        TestUnit(
            target="postgres",
            name="postgres",
            platform="linux",
            runner_labels=("ubuntu-22.04",),
            environments=(),
        ),
    ]


def test_expand_multi_label_runner_is_a_single_selection():
    targets = [TargetDefinition("postgres", runners={"linux": ["label-a", "label-b"]})]

    units = expand_test_units(targets)

    assert units[0].runner_labels == ("label-a", "label-b")


def test_expand_platform_override_adds_platform_suffix():
    targets = [TargetDefinition("postgres", platforms=("linux", "windows"))]

    units = expand_test_units(targets)

    assert [(u.platform, u.name, u.runner_labels) for u in units] == [
        ("linux", "postgres on Linux", ("ubuntu-22.04",)),
        ("windows", "postgres on Windows", ("windows-2022",)),
    ]


def test_expand_uses_injected_resolved_display_name():
    # The display name is resolved upstream (from ddev's Integration.display_name) and injected;
    # this package does not reproduce the override/manifest precedence.
    targets = [TargetDefinition("postgres", display_name="Resolved Name")]

    units = expand_test_units(targets)

    assert units[0].name == "Resolved Name"


def test_expand_display_name_falls_back_to_target_name():
    targets = [TargetDefinition("postgres")]

    units = expand_test_units(targets)

    assert units[0].name == "postgres"


def test_expand_respects_display_order_override():
    targets = [
        TargetDefinition("postgres"),
        TargetDefinition("ddev"),
        TargetDefinition("datadog_checks_base"),
    ]

    units = expand_test_units(targets)

    assert [u.target for u in units] == ["ddev", "datadog_checks_base", "postgres"]


def test_expand_e2e_availability_is_per_environment():
    targets = [TargetDefinition("postgres", environments=(env("py3.11", e2e=True), env("py3.12", e2e=False)))]

    units = expand_test_units(targets, split_environments=True)

    assert [(u.environments[0].name, u.environments[0].e2e_available) for u in units] == [
        ("py3.11", True),
        ("py3.12", False),
    ]


def test_expand_e2e_availability_is_platform_specific():
    # Environments are pre-routed to platforms by the provider; E2E differs per platform.
    targets = [
        TargetDefinition(
            "postgres",
            platforms=("linux", "windows"),
            environments=(env("py3.11-linux", "linux", e2e=True), env("py3.11-windows", "windows", e2e=False)),
        ),
    ]

    units = expand_test_units(targets, split_environments=True)

    assert [(u.platform, u.environments[0].name, u.environments[0].e2e_available) for u in units] == [
        ("linux", "py3.11-linux", True),
        ("windows", "py3.11-windows", False),
    ]


def test_expand_unsplit_runs_all_environments_together_preserving_e2e_subset():
    targets = [
        TargetDefinition("postgres", environments=(env("py3.11", e2e=False), env("py3.12", e2e=True))),
    ]

    units = expand_test_units(targets, split_environments=False)

    # One unit per target/platform covering every environment, preserving order and each
    # environment's E2E flag so downstream can build a unit job plus an E2E job over the subset.
    assert units == [
        TestUnit(
            target="postgres",
            name="postgres",
            platform="linux",
            runner_labels=("ubuntu-22.04",),
            environments=(env("py3.11", e2e=False), env("py3.12", e2e=True)),
        ),
    ]
    unit = units[0]
    assert [e.name for e in unit.environments] == ["py3.11", "py3.12"]
    assert [e.name for e in unit.environments if e.e2e_available] == ["py3.12"]


def test_expand_carries_unit_only_and_e2e_only_facets():
    # A unit-only environment (test_env), an E2E-only environment (e2e_env), and a both-facet one.
    targets = [
        TargetDefinition(
            "postgres",
            environments=(
                env("py3.11", unit=True, e2e=False),
                env("py3.11-e2e", unit=False, e2e=True),
                env("py3.12", unit=True, e2e=True),
            ),
        ),
    ]

    units = expand_test_units(targets, split_environments=True)

    facets = [
        (u.environments[0].name, u.environments[0].test_available, u.environments[0].e2e_available) for u in units
    ]
    assert facets == [
        ("py3.11", True, False),
        ("py3.11-e2e", False, True),
        ("py3.12", True, True),
    ]


def test_expand_environmentless_target_is_single_unit_regardless_of_split():
    targets = [TargetDefinition("datadog_checks_base")]

    split = expand_test_units(targets, split_environments=True)
    unsplit = expand_test_units(targets, split_environments=False)

    assert split == unsplit
    assert [(u.target, u.environments) for u in split] == [("datadog_checks_base", ())]
