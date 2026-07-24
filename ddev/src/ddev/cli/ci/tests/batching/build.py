# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The single public entry point that turns changed files into deterministic test units.

:func:`build_test_units` composes the whole pipeline: it runs the affected-target rules against
ddev's integration registry, reads CI overrides from ``repo.config``, resolves each target's
display name and platforms from ddev, obtains resolved environments through an injected
:class:`~ddev.cli.ci.tests.batching.units.EnvironmentProvider`, and expands everything into
ordered :class:`~ddev.cli.ci.tests.batching.units.TestUnit` values.

The environment provider is the seam that keeps callers decoupled from Hatch: production uses
:class:`HatchEnvironmentProvider` (ddev's ``list_environments``), while tests inject a plain
callable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.batching.assembly import create_test_batches
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

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.cli.ci.tests.batching.git import ChangedFile
    from ddev.cli.ci.tests.batching.targets import TargetRule
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.integration.core import Integration
    from ddev.repo.core import Repository
    from ddev.utils.hatch import Environment
    from ddev.utils.platform import Platform


def build_test_units(
    repo: Repository,
    changed_files: Sequence[ChangedFile],
    *,
    environment_provider: EnvironmentProvider,
    split_environments: bool = True,
    rules: Sequence[TargetRule] | None = None,
) -> list[TestUnit]:
    """Turn a set of changed files into the complete, deterministic list of test units.

    When ``rules`` is ``None`` the default rule set is built from the repository, gating the
    repository-wide rule on whether ``repo`` is the core repository.
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
        platforms = resolve_platforms(ci_override.get("platforms", []), _supported_os(integration))
        definitions.append(
            TargetDefinition(
                name=name,
                display_name=integration.display_name,
                platforms=tuple(platforms),
                runners=ci_override.get("runners", {}),
                environments=tuple(environment_provider(integration, platforms)),
            )
        )

    return expand_test_units(definitions, split_environments=split_environments)


def build_test_batches(
    repo: Repository,
    changed_files: Sequence[ChangedFile],
    *,
    environment_provider: EnvironmentProvider,
    config: BatchingConfig,
    strategy: BatchStrategy = default_strategy,
    rules: Sequence[TargetRule] | None = None,
) -> list[TestBatch]:
    """Turn changed files into the complete, ordered list of ``TestBatch`` messages.

    The pipeline obtains test units through the public :func:`build_test_units` boundary (never by
    composing affected-target and unit-expansion internals here) and expands each resolved
    environment into one concrete ``target + environment + platform`` job, so the final plan always
    has one job per actual environment. It then applies the (injected or default) batching
    ``strategy``, validates the resulting partition independently of that strategy, and constructs
    deterministically numbered messages. Empty input yields no batches.
    """
    units = build_test_units(
        repo,
        changed_files,
        environment_provider=environment_provider,
        rules=rules,
    )
    jobs = expand_batch_jobs(units)
    job_groups = strategy(jobs, capacity=config.max_jobs_per_batch, config=config)
    validate_batches(job_groups, jobs, capacity=config.max_jobs_per_batch, config=config)
    return create_test_batches(job_groups)


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
    """An :class:`EnvironmentProvider` backed by ddev's Hatch integration.

    Environment names and facet flags come from ddev's ``list_environments``; facet filtering
    and platform routing are delegated to :func:`resolve_hatch_environments`.
    """

    platform: Platform

    def __call__(self, integration: Integration, platforms: Sequence[str]) -> list[ResolvedEnvironment]:
        from ddev.utils.hatch import list_environments

        return resolve_hatch_environments(list_environments(self.platform, integration), platforms)


def resolve_hatch_environments(
    environments: Sequence[Environment],
    platforms: Sequence[str],
) -> list[ResolvedEnvironment]:
    """Map ddev ``Environment`` values onto target platforms, keeping both facet flags.

    An environment is included when enabled for either the unit facet (``test_env``) or the E2E
    facet (``e2e_env``); both flags are preserved on each resolved environment. An environment
    with an explicit ``platforms`` constraint (which ddev populates from a ``hatch.toml``
    ``overrides.matrix.os.platforms`` mapping) is routed only to the intersection of that
    constraint with the target's platforms, so a Windows-only environment never lands on Linux.
    An unconstrained environment is routed to a single default platform (the target's first) and
    is never cross-produced across the target's platforms.
    """
    if not platforms:
        return []

    default_platform = platforms[0]
    resolved: list[ResolvedEnvironment] = []
    for environment in environments:
        if not (environment.test_env or environment.e2e_env):
            continue

        candidate_platforms = list(environment.platforms) if environment.platforms else [default_platform]
        for platform_id in candidate_platforms:
            if platform_id in platforms:
                resolved.append(
                    ResolvedEnvironment(
                        name=environment.name,
                        platform=platform_id,
                        test_available=environment.test_env,
                        e2e_available=environment.e2e_env,
                    )
                )
    return resolved
