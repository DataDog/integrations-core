# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Public entry points that turn changed files into test units and batches."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.batching.jobs import expand_batch_jobs
from ddev.cli.ci.tests.batching.strategy import BatchStrategy, default_strategy
from ddev.cli.ci.tests.batching.targets import (
    RegistryRepositoryFacts,
    default_target_rules,
    find_affected_targets,
)
from ddev.cli.ci.tests.batching.units import (
    TargetDefinition,
    TestUnit,
    expand_test_units,
    resolve_platforms,
)
from ddev.cli.ci.tests.batching.validation import validate_batches
from ddev.cli.ci.tests.messages import TestBatch

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.batching.targets import TargetRule
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob
    from ddev.integration.core import Integration
    from ddev.repo.core import Repository
    from ddev.utils.git import ChangedFile

logger = logging.getLogger(__name__)


def build_test_units(
    repo: Repository,
    changed_files: Sequence[ChangedFile],
    *,
    environment_provider: EnvironmentProvider,
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
                supports_minimum_base_package=supports_minimum_base_package(integration),
            )
        )

    return expand_test_units(definitions)


def supports_minimum_base_package(integration: Integration) -> bool:
    """Whether testing *integration* against the minimum base package differs from a normal run.

    Mirrors the condition `ddev test --compat` applies before pinning the base package version, so a
    target it would not pin is never replicated.
    """
    return (
        integration.is_package and integration.is_integration and integration.minimum_base_package_version is not None
    )


def build_test_batches(
    repo: Repository,
    changed_files: Sequence[ChangedFile],
    *,
    environment_provider: EnvironmentProvider,
    config: BatchingConfig,
    strategy: BatchStrategy = default_strategy,
    rules: Sequence[TargetRule] | None = None,
    minimum_base_package: bool = False,
) -> list[TestBatch]:
    """Turn changed files into the complete, ordered list of `TestBatch` messages.

    The partition is validated independently of the strategy that produced it. Empty input yields
    no batches.
    """
    units = build_test_units(
        repo,
        changed_files,
        environment_provider=environment_provider,
        rules=rules,
    )
    jobs = expand_batch_jobs(units, minimum_base_package=minimum_base_package)
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
