# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Expansion of affected targets into test units."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, NamedTuple, Protocol

from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.utils.platform import PlatformName

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ddev.integration.core import Integration


class PlatformSpec(NamedTuple):
    """Display name and default GitHub runner image for one platform."""

    name: str
    image: str


# Kept in sync by hand with `ci_matrix.PLATFORMS`, which CI still uses and which cannot import from
# here because it has to run standalone. A runner image changed in one place and not the other makes
# the two plans disagree.
PLATFORMS: dict[PlatformName, PlatformSpec] = {
    PlatformName.LINUX: PlatformSpec("Linux", "ubuntu-22.04"),
    PlatformName.WINDOWS: PlatformSpec("Windows", "windows-2022"),
    PlatformName.MACOS: PlatformSpec("macOS", "macos-14-large"),
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

# Job names end up in file paths, so characters Windows reserves must be replaced.
# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions
JOB_NAME_RESERVED_PATTERN = re.compile(r'[<>:"/\\|?*]')


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedEnvironment:
    """One environment a target runs, already routed onto a platform.

    The two availability flags carry intent rather than a decision. They exist so a later change can
    split unit and E2E work into separate jobs per environment and platform, which is why they are
    per-environment here instead of per-target. Nothing splits on them yet: the workflow runs both
    kinds of test and each works out at runtime whether it has anything to do, which is how CI
    behaves today.

    Splitting is deferred because Hatch cannot answer the question at planning time. It resolves
    `platform.*` overrides against the machine it runs on, so `platform.windows.e2e-env = false`
    (ibm_mq, ibm_ace, network, sqlserver) is invisible when planning on Linux, and it resolves
    `env.*` overrides against the ambient environment, so azure_iot_edge's E2E availability depends
    on a secret the planner does not have. Neither is knowable from one host. Note the `env.*` case
    fails toward reporting no E2E work, so it drops coverage rather than wasting compute once
    anything gates on these flags. The per-integration tooling configuration that replaces
    `manifest.json` and `.ddev/config.toml` is where each environment will declare this
    deterministically, and that is what these flags should be driven from.
    """

    name: str
    platform: PlatformName
    python_version: str  # `major.minor`, picks both the runner Python and the E2E Agent image
    # TODO(manifest): drive these from the per-integration tooling configuration planned to replace
    # `manifest.json`, which can declare them per platform deterministically, and split unit and
    # E2E work into separate jobs once it can.
    test_available: bool = True  # ddev's `test_env`
    e2e_available: bool = False  # ddev's `e2e_env`


class EnvironmentProvider(Protocol):
    """Resolves the environments an integration runs, routed onto the given platforms."""

    def __call__(self, integration: Integration, platforms: Sequence[PlatformName]) -> list[ResolvedEnvironment]: ...


@dataclass(frozen=True)
class TargetDefinition:
    """A single target to expand, with everything expansion needs already resolved."""

    name: str
    display_name: str | None = None
    platforms: tuple[PlatformName, ...] = (PlatformName.LINUX,)
    runners: Mapping[str, Sequence[str]] = field(default_factory=dict)
    environments: tuple[ResolvedEnvironment, ...] = ()
    # Whether `ddev test --compat` would pin this target's base package. Resolved from the
    # integration itself, because only a shipped integration that pins a `datadog-checks-base`
    # version has an older one to test against.
    supports_minimum_base_package: bool = False


@dataclass(frozen=True)
class TestUnit:
    """One target, on one platform, in one environment. Becomes exactly one job.

    `name` is already unique across the plan and is reused verbatim as the job's display name.
    """

    # Prevent pytest from collecting this domain class as a test case.
    __test__: ClassVar[bool] = False

    target: str
    name: str
    platform: PlatformName
    runner_labels: tuple[str, ...]
    environment: ResolvedEnvironment
    supports_minimum_base_package: bool = False


def normalize_job_name(job_name: str) -> str:
    """Replace characters reserved on Windows so the name can be used in file paths."""
    return JOB_NAME_RESERVED_PATTERN.sub("_", job_name)


def parse_platform_name(value: str, *, target: str) -> PlatformName:
    """Convert a configured platform string into a `PlatformName`, naming the target on failure."""
    try:
        return PlatformName(value.lower())
    except ValueError:
        supported = ", ".join(sorted(PLATFORMS))
        raise PlanningError(f"Unsupported platform for `{target}`: {value} (expected one of {supported})") from None


def resolve_platforms(
    platform_override: Sequence[str],
    supported_os: Sequence[str],
    *,
    target: str,
) -> list[PlatformName]:
    """Resolve the platforms a target runs on, from CI overrides then its supported OS list.

    Only the override is parsed strictly. It is hand-written configuration, so a name we do not
    recognize is a mistake worth failing on, and a repeated one would plan two identically named
    jobs.
    """
    if platform_override:
        platforms = [parse_platform_name(value, target=target) for value in platform_override]
        if len(set(platforms)) != len(platforms):
            raise PlanningError(f"Duplicate platform in the CI `platforms` override for `{target}`")
        return platforms

    # `manifest.json` advertises platforms ddev has no runner for, such as AIX, so the supported OS
    # list only decides Windows-exclusivity rather than being parsed. Only a Windows-exclusive
    # target runs on Windows by default; anything else runs on Linux alone, and extra platforms are
    # opt-in through the CI `platforms` override handled above.
    if [value.lower() for value in supported_os] == [str(PlatformName.WINDOWS)]:
        return [PlatformName.WINDOWS]

    return [PlatformName.LINUX]


def group_environments_by_platform(
    environments: Sequence[ResolvedEnvironment],
) -> dict[PlatformName, list[ResolvedEnvironment]]:
    """Group resolved environments by their target platform, preserving order."""
    grouped: dict[PlatformName, list[ResolvedEnvironment]] = {}
    for environment in environments:
        grouped.setdefault(environment.platform, []).append(environment)
    return grouped


def _display_order_key(target: str) -> tuple[int, str]:
    return DISPLAY_ORDER_OVERRIDE.get(target, len(DISPLAY_ORDER_OVERRIDE)), target


def expand_test_units(targets: Sequence[TargetDefinition]) -> list[TestUnit]:
    """Expand targets into deterministically ordered test units, one per resolved environment.

    A platform whose environments are all constrained elsewhere gets no units, which is the
    constraint working as intended rather than an error.
    """
    ordered_targets = sorted(targets, key=lambda target: _display_order_key(target.name))

    units: list[TestUnit] = []
    for target in ordered_targets:
        if not target.environments:
            raise PlanningError(f"{target.name!r} reached unit expansion with no environments")

        display_name = target.display_name or target.name
        environments_by_platform = group_environments_by_platform(target.environments)

        for platform_id in target.platforms:
            platform = PLATFORMS[platform_id]
            base_name = display_name
            if len(target.platforms) > 1:
                base_name += f" on {platform.name}"
            job_name = normalize_job_name(base_name)
            runner_labels = tuple(target.runners.get(platform_id, [platform.image]))

            platform_environments = environments_by_platform.get(platform_id, [])
            if not platform_environments:
                logger.warning("%s runs on %s but no environment tests it", target.name, platform_id)
                continue

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
                        supports_minimum_base_package=target.supports_minimum_base_package,
                    )
                )

    return units
