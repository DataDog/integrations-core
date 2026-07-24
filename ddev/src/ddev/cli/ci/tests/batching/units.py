# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Deterministic expansion of affected targets into typed test-planning units.

A test unit is a planning unit — a target with one platform and an explicit environment
selection. It is not a concrete CI job: downstream planning may expand a single unit into
multiple facet jobs (a unit-test job for ``test_env`` environments and an E2E job for
``e2e_env`` environments).

Environments are supplied pre-resolved through an :class:`EnvironmentProvider`, so this module
does not compute the Hatch matrix. Each resolved environment carries both facet flags
(``test_env`` and ``e2e_env``), so one target can emit both facets and callers can select the
unit-only or E2E-only subset.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, NamedTuple, Protocol

if TYPE_CHECKING:
    from ddev.integration.core import Integration


class Platform(NamedTuple):
    name: str
    image: str


PLATFORMS: dict[str, Platform] = {
    "linux": Platform("Linux", "ubuntu-22.04"),
    "windows": Platform("Windows", "windows-2022"),
    "macos": Platform("macOS", "macos-14-large"),
}

# Targets rendered before everything else, in this order.
DISPLAY_ORDER_OVERRIDE: dict[str, int] = {
    name: index
    for index, name in enumerate(
        (
            "ddev",
            "datadog_checks_base",
            "datadog_checks_dev",
            "datadog_checks_downloader",
        )
    )
}

# Characters that are reserved (illegal) in Windows file names. Job names are later used to
# construct unique file paths (e.g. per-job artifact/report directories), so any of these
# characters must be replaced to keep those paths valid across platforms.
# See https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions
JOB_NAME_RESERVED_PATTERN = re.compile(r'[<>:"/\\|?*]')


@dataclass(frozen=True)
class ResolvedEnvironment:
    """A concrete environment resolved for a target: exactly what expansion consumes.

    ``test_available`` is the unit-test facet (ddev's ``test_env``) and ``e2e_available`` is the
    E2E facet (``e2e_env``). Both are kept so callers can create unit work only for
    ``test_available`` environments and E2E work only for ``e2e_available`` environments.
    """

    name: str
    platform: str
    test_available: bool = True
    e2e_available: bool = False


class EnvironmentProvider(Protocol):
    """Resolves the environments an integration runs, routed onto the given platforms.

    The caller already holds the ddev :class:`Integration`, so it is passed directly. Production
    implementations source environments from ddev's Hatch model; tests inject synthetic ones.
    """

    def __call__(self, integration: Integration, platforms: Sequence[str]) -> list[ResolvedEnvironment]: ...


@dataclass(frozen=True)
class TargetDefinition:
    """Fully digested facts for a single target used during expansion.

    Everything here is already resolved upstream (in production from ddev): ``display_name``
    from ``Integration.display_name``, ``platforms`` from CI overrides/manifest, ``runners``
    from CI overrides, and ``environments`` from the environment provider.
    """

    name: str
    display_name: str | None = None
    platforms: tuple[str, ...] = ("linux",)
    runners: Mapping[str, Sequence[str]] = field(default_factory=dict)
    environments: tuple[ResolvedEnvironment, ...] = ()


@dataclass(frozen=True)
class TestUnit:
    """A single deterministic test-planning unit produced from an affected target.

    A unit is not a concrete CI job: downstream planning may expand it into multiple facet jobs
    (unit and E2E). ``environments`` is the explicit, ordered selection this unit covers:
    exactly one when environments are split, every environment for the platform when they are
    not, and empty for targets without environment definitions. Each entry keeps its own facet
    flags.
    """

    # Prevent pytest from collecting this domain class as a test case.
    __test__: ClassVar[bool] = False

    target: str
    name: str
    platform: str
    runner_labels: tuple[str, ...]
    environments: tuple[ResolvedEnvironment, ...]


def normalize_job_name(job_name: str) -> str:
    """Replace characters reserved on Windows so the name can be used in file paths."""
    return JOB_NAME_RESERVED_PATTERN.sub("_", job_name)


def resolve_platforms(platform_override: Sequence[str], supported_os: Sequence[str]) -> list[str]:
    """Resolve the platforms a target runs on from CI overrides then its supported OS list."""
    if platform_override:
        return list(platform_override)

    platform_ids = [value.lower() for value in supported_os]
    # A target that supports multiple operating systems runs on Linux only by default; a
    # Windows-exclusive target runs on Windows. Testing a multi-OS target on additional
    # platforms (e.g. Windows for path-handling coverage) is opt-in via the CI ``platforms``
    # override, which takes precedence above.
    if platform_ids != ["windows"]:
        platform_ids = ["linux"]

    return platform_ids


def group_environments_by_platform(
    environments: Sequence[ResolvedEnvironment],
) -> dict[str, list[ResolvedEnvironment]]:
    """Group resolved environments by their target platform, preserving order."""
    grouped: dict[str, list[ResolvedEnvironment]] = {}
    for environment in environments:
        grouped.setdefault(environment.platform, []).append(environment)
    return grouped


def _display_order_key(target: str) -> tuple[int, str]:
    return DISPLAY_ORDER_OVERRIDE.get(target, len(DISPLAY_ORDER_OVERRIDE)), target


def expand_test_units(
    targets: Sequence[TargetDefinition],
    *,
    split_environments: bool = True,
) -> list[TestUnit]:
    """Expand digested targets into deterministically ordered typed test units.

    When ``split_environments`` is true each resolved environment becomes its own unit;
    otherwise a single unit per target/platform covers every environment together. Targets
    without environments always produce a single unit with an empty selection.
    """
    ordered_targets = sorted(targets, key=lambda target: _display_order_key(target.name))

    units: list[TestUnit] = []
    for target in ordered_targets:
        display_name = target.display_name or target.name
        environments_by_platform = group_environments_by_platform(target.environments)

        for platform_id in target.platforms:
            if platform_id not in PLATFORMS:
                raise ValueError(f"Unsupported platform for `{target.name}`: {platform_id}")

            platform = PLATFORMS[platform_id]
            base_name = display_name
            if len(target.platforms) > 1:
                base_name += f" on {platform.name}"
            job_name = normalize_job_name(base_name)
            runner_labels = tuple(target.runners.get(platform_id, [platform.image]))

            platform_environments = environments_by_platform.get(platform_id, [])
            if split_environments and platform_environments:
                for environment in platform_environments:
                    name = job_name if environment.name == target.name else f"{job_name} ({environment.name})"
                    units.append(
                        TestUnit(
                            target=target.name,
                            name=name,
                            platform=platform_id,
                            runner_labels=runner_labels,
                            environments=(environment,),
                        )
                    )
            else:
                # A single unit covers every environment for this platform (or none for
                # environmentless targets), keeping each environment's identity and E2E flag.
                units.append(
                    TestUnit(
                        target=target.name,
                        name=job_name,
                        platform=platform_id,
                        runner_labels=runner_labels,
                        environments=tuple(platform_environments),
                    )
                )

    return units
