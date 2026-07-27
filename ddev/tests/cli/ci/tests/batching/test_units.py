# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import functools

import pytest

from ddev.cli.ci.tests.batching.units import (
    TargetDefinition,
    TestUnit,
    expand_test_units,
    normalize_job_name,
    resolve_platforms,
)
from tests.helpers.batching import DEFAULT_PYTHON_VERSION, env

expand = functools.partial(expand_test_units, default_python_version=DEFAULT_PYTHON_VERSION)


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


def test_expand_gives_each_environment_its_own_unit():
    targets = [TargetDefinition("postgres", environments=(env("py3.11", e2e=True), env("py3.12", e2e=True)))]

    assert expand(targets) == [
        TestUnit(
            target="postgres",
            name="postgres (py3.11)",
            platform="linux",
            runner_labels=("ubuntu-22.04",),
            environment=env("py3.11", e2e=True),
        ),
        TestUnit(
            target="postgres",
            name="postgres (py3.12)",
            platform="linux",
            runner_labels=("ubuntu-22.04",),
            environment=env("py3.12", e2e=True),
        ),
    ]


def test_expand_preserves_environment_order():
    targets = [
        TargetDefinition(
            "postgres",
            environments=(env("py3.11-9"), env("py3.11-10"), env("py3.12-9"), env("py3.12-10")),
        ),
    ]

    assert [u.environment.name for u in expand(targets)] == ["py3.11-9", "py3.11-10", "py3.12-9", "py3.12-10"]


def test_expand_environmentless_target_gets_an_unnamed_environment():
    units = expand([TargetDefinition("postgres")])

    assert units == [
        TestUnit(
            target="postgres",
            name="postgres",
            platform="linux",
            runner_labels=("ubuntu-22.04",),
            environment=env("", python_version=DEFAULT_PYTHON_VERSION),
        ),
    ]


def test_expand_environmentless_target_uses_the_default_python_version():
    units = expand_test_units([TargetDefinition("postgres")], default_python_version="3.11")

    assert units[0].environment.python_version == "3.11"


def test_expand_environment_named_after_its_target_does_not_repeat_in_the_name():
    units = expand([TargetDefinition("postgres", environments=(env("postgres"),))])

    assert units[0].name == "postgres"


def test_expand_carries_the_environment_python_version():
    targets = [TargetDefinition("postgres", environments=(env("py3.11", python_version="3.11"),))]

    assert expand(targets)[0].environment.python_version == "3.11"


def test_expand_multi_label_runner_is_a_single_selection():
    units = expand([TargetDefinition("postgres", runners={"linux": ["label-a", "label-b"]})])

    assert units[0].runner_labels == ("label-a", "label-b")


def test_expand_platform_override_adds_platform_suffix():
    units = expand([TargetDefinition("postgres", platforms=("linux", "windows"))])

    assert [(u.platform, u.name, u.runner_labels) for u in units] == [
        ("linux", "postgres on Linux", ("ubuntu-22.04",)),
        ("windows", "postgres on Windows", ("windows-2022",)),
    ]


def test_expand_uses_injected_resolved_display_name():
    # The display name is resolved upstream (from ddev's Integration.display_name) and injected;
    # this package does not reproduce the override/manifest precedence.
    units = expand([TargetDefinition("postgres", display_name="Resolved Name")])

    assert units[0].name == "Resolved Name"


def test_expand_display_name_falls_back_to_target_name():
    assert expand([TargetDefinition("postgres")])[0].name == "postgres"


def test_expand_respects_display_order_override():
    targets = [
        TargetDefinition("postgres"),
        TargetDefinition("ddev"),
        TargetDefinition("datadog_checks_base"),
    ]

    assert [u.target for u in expand(targets)] == ["ddev", "datadog_checks_base", "postgres"]


def test_expand_rejects_an_unsupported_platform():
    with pytest.raises(ValueError, match="Unsupported platform"):
        expand([TargetDefinition("postgres", platforms=("solaris",))])


def test_expand_e2e_availability_is_per_environment():
    targets = [TargetDefinition("postgres", environments=(env("py3.11", e2e=True), env("py3.12", e2e=False)))]

    assert [(u.environment.name, u.environment.e2e_available) for u in expand(targets)] == [
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

    assert [(u.platform, u.environment.name, u.environment.e2e_available) for u in expand(targets)] == [
        ("linux", "py3.11-linux", True),
        ("windows", "py3.11-windows", False),
    ]


def test_expand_platform_without_environments_still_gets_a_unit():
    # A target on two platforms whose environments all route to one of them still runs on both:
    # the uncovered platform gets an environmentless unit, matching ci_matrix.
    targets = [
        TargetDefinition(
            "datadog_checks_base",
            platforms=("linux", "windows"),
            environments=(env("py3.13", "linux"),),
        ),
    ]

    assert [(u.platform, u.environment.name) for u in expand(targets)] == [
        ("linux", "py3.13"),
        ("windows", ""),
    ]


def test_expand_carries_unit_only_and_e2e_only_facets():
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

    facets = [(u.environment.name, u.environment.test_available, u.environment.e2e_available) for u in expand(targets)]
    assert facets == [
        ("py3.11", True, False),
        ("py3.11-e2e", False, True),
        ("py3.12", True, True),
    ]
