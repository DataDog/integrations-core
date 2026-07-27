# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Deterministic expansion of affected targets into typed test-planning units.

A test unit is a planning unit: one target, on one platform, running one resolved environment (or
none, for a target that defines no environments). It maps one-to-one onto the concrete job that
:mod:`~ddev.cli.ci.tests.batching.jobs` builds from it, so a unit's name is already the final job
display name.

Environments are supplied pre-resolved through an :class:`EnvironmentProvider`, so this module
does not compute the Hatch matrix. Each resolved environment carries the Python version it runs
under and both facet flags (``test_env`` and ``e2e_env``), which become attributes of the single
job the unit produces.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, NamedTuple, Protocol

if TYPE_CHECKING:
    from ddev.integration.core import Integration


class PlatformSpec(NamedTuple):
    """Display name and default GitHub runner image for one test-matrix platform."""

    name: str
    image: str


PLATFORMS: dict[str, PlatformSpec] = {
    "linux": PlatformSpec("Linux", "ubuntu-22.04"),
    "windows": PlatformSpec("Windows", "windows-2022"),
    "macos": PlatformSpec("macOS", "macos-14-large"),
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

    ``python_version`` is the ``major.minor`` interpreter the environment runs under, used both to
    set up Python on the runner and to select the E2E Agent image. ``test_available`` is the
    unit-test facet (ddev's ``test_env``) and ``e2e_available`` is the E2E facet (``e2e_env``);
    both are kept so a job can declare exactly which facets it must produce.
    """

    name: str
    platform: str
    python_version: str
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

    ``environment`` is the one resolved environment this unit covers. A target that defines no
    environments on a platform gets an environment with an empty ``name``, meaning its tests run
    without an environment selection, the way ``ci_matrix`` emits a job with no ``target-env``.
    ``name`` is already unique across the plan, so downstream job construction reuses it verbatim.
    """

    # Prevent pytest from collecting this domain class as a test case.
    __test__: ClassVar[bool] = False

    target: str
    name: str
    platform: str
    runner_labels: tuple[str, ...]
    environment: ResolvedEnvironment


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


def expand_test_units(targets: Sequence[TargetDefinition], *, default_python_version: str) -> list[TestUnit]:
    """Expand digested targets into deterministically ordered typed test units.

    Each resolved environment becomes its own unit. A target with no environments on a platform
    produces a single unit for that platform whose environment has an empty name and runs under
    ``default_python_version``, since there is no environment to read a Python version from.
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

            platform_environments = environments_by_platform.get(platform_id, []) or [
                ResolvedEnvironment(name="", platform=platform_id, python_version=default_python_version)
            ]
            for environment in platform_environments:
                if environment.name and environment.name != target.name:
                    name = f"{job_name} ({environment.name})"
                else:
                    name = job_name
                units.append(
                    TestUnit(
                        target=target.name,
                        name=name,
                        platform=platform_id,
                        runner_labels=runner_labels,
                        environment=environment,
                    )
                )

    return units
