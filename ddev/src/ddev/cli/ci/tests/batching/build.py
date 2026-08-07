# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Public entry points that turn changed files into test units and batches."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.cli.ci.tests.batching.jobs import expand_batch_jobs
from ddev.cli.ci.tests.batching.strategy import BatchStrategy, default_strategy
from ddev.cli.ci.tests.batching.targets import (
    RegistryRepositoryFacts,
    default_target_rules,
    find_affected_targets,
)
from ddev.cli.ci.tests.batching.units import (
    ResolvedEnvironment,
    TargetDefinition,
    TestUnit,
    expand_test_units,
    resolve_platforms,
)
from ddev.cli.ci.tests.batching.validation import validate_batches
from ddev.cli.ci.tests.messages import TestBatch
from ddev.e2e.agent_images import PYTHON_VERSION_PATTERN

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.batching.targets import TargetRule
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob
    from ddev.integration.core import Integration
    from ddev.repo.core import Repository
    from ddev.utils.git import ChangedFile
    from ddev.utils.hatch import Environment
    from ddev.utils.platform import Platform, PlatformName

logger = logging.getLogger(__name__)


def build_test_units(
    repo: Repository,
    changed_files: Sequence[ChangedFile],
    *,
    environment_provider: EnvironmentProvider,
    default_python_version: str,
    rules: Sequence[TargetRule] | None = None,
) -> list[TestUnit]:
    """Turn changed files into the complete, deterministic list of test units.

    Without explicit `rules`, the default set is used, with the repository-wide rule enabled only
    for the core repository.
    """
    if rules is None:
        rules = default_target_rules(is_core=repo.name == "core")

    facts = RegistryRepositoryFacts(repo.integrations)
    target_names = find_affected_targets(changed_files, facts, rules=rules)

    definitions: list[TargetDefinition] = []
    for name in target_names:
        ci_override = repo.config.get(f"/overrides/ci/{name}", {}) or {}
        if ci_override.get("exclude", False):
            continue

        integration = repo.integrations.get(name)
        platforms = resolve_platforms(ci_override.get("platforms", []), _supported_os(integration), target=name)
        environments = tuple(environment_provider(integration, platforms))
        if not environments:
            # A `hatch.toml` makes a target testable, so one that enables no test or E2E
            # environment contradicts itself. Deliberate opt-out is `overrides.ci.<target>.exclude`.
            logger.warning("%s has a hatch.toml but no testable environment", name)
            continue

        definitions.append(
            TargetDefinition(
                name=name,
                display_name=integration.display_name,
                platforms=tuple(platforms),
                runners=ci_override.get("runners", {}),
                environments=environments,
            )
        )

    return expand_test_units(definitions, default_python_version=default_python_version)


def build_test_batches(
    repo: Repository,
    changed_files: Sequence[ChangedFile],
    *,
    environment_provider: EnvironmentProvider,
    config: BatchingConfig,
    default_python_version: str,
    strategy: BatchStrategy = default_strategy,
    rules: Sequence[TargetRule] | None = None,
) -> list[TestBatch]:
    """Turn changed files into the complete, ordered list of `TestBatch` messages.

    The partition is validated independently of the strategy that produced it. Empty input yields
    no batches.
    """
    units = build_test_units(
        repo,
        changed_files,
        environment_provider=environment_provider,
        default_python_version=default_python_version,
        rules=rules,
    )
    jobs = expand_batch_jobs(units)
    job_groups = strategy(jobs, config=config)
    validate_batches(job_groups, jobs, config=config)
    return create_test_batches(job_groups)


def create_test_batches(job_groups: Sequence[Sequence[BatchJob]]) -> list[TestBatch]:
    """Build ordered `TestBatch` messages, numbering from `batch-01` on every call.

    The message `id` is set to the same value as `batch_id` for now; processors correlate on
    `batch_id`, so the two are free to diverge later.
    """
    batches: list[TestBatch] = []
    for index, group in enumerate(job_groups, start=1):
        batch_id = f"batch-{index:02d}"
        integrations = list(dict.fromkeys(job.target for job in group))
        batches.append(
            TestBatch(
                id=batch_id,
                batch_id=batch_id,
                job_list=list(group),
                jobs_count=len(group),
                integrations=integrations,
            )
        )
    return batches


def _supported_os(integration: Integration) -> list[str]:
    # TODO(manifest): platform detection reads `manifest.json` classifier tags. A planned change
    # will remove ddev tooling's dependency on the manifest; revisit this once that lands.
    supported_os: list[str] = []
    for classifier_tag in integration.manifest.get("/tile/classifier_tags", []) or []:
        key, _, value = classifier_tag.partition("::")
        if key == "Supported OS":
            supported_os.append(value)
    return supported_os


@dataclass(frozen=True, eq=False)
class HatchEnvironmentProvider:
    """An `EnvironmentProvider` backed by ddev's Hatch integration."""

    platform: Platform
    default_python_version: str

    def __call__(self, integration: Integration, platforms: Sequence[PlatformName]) -> list[ResolvedEnvironment]:
        from ddev.utils.hatch import list_environments

        return resolve_hatch_environments(
            list_environments(self.platform, integration),
            platforms,
            default_python_version=self.default_python_version,
        )


def resolve_hatch_environments(
    environments: Sequence[Environment],
    platforms: Sequence[PlatformName],
    *,
    default_python_version: str,
) -> list[ResolvedEnvironment]:
    """Map ddev `Environment` values onto target platforms, keeping environments that test anything.

    An environment constrained to specific platforms is routed only to those the target also runs
    on; an unconstrained one runs on every platform the target runs on.

    The Python version comes from Hatch's own `python` value, never from the environment name,
    which only encodes it by convention.
    """
    if not platforms:
        return []

    by_name = {str(platform): platform for platform in platforms}
    resolved: list[ResolvedEnvironment] = []
    for environment in environments:
        if not (environment.test_env or environment.e2e_env):
            continue

        if environment.platforms:
            # Raw configuration, so a platform ddev does not target drops out of the intersection
            # instead of failing the plan.
            candidate_platforms = [by_name[name] for name in environment.platforms if name in by_name]
        else:
            candidate_platforms = list(platforms)

        python_version = environment.python or default_python_version
        if not PYTHON_VERSION_PATTERN.match(python_version):
            raise PlanningError(
                f'Environment {environment.name!r} reports Python {python_version!r}; '
                f'expected a `major.minor` version such as `3.13`'
            )

        for platform in candidate_platforms:
            resolved.append(
                ResolvedEnvironment(
                    name=environment.name,
                    platform=platform,
                    python_version=python_version,
                    test_available=environment.test_env,
                    e2e_available=environment.e2e_env,
                )
            )
    return resolved
