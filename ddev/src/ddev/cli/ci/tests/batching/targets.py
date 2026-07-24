# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Composable affected-target discovery.

Discovery is an ordered composition of independent rules. Each rule receives the normalized
changed files and a narrow read-only view of the repository; a deterministic ordered union
combines their results and applies the testability/exclusion policy.

Testability is sourced from ddev's integration registry (``Integration.is_testable`` and
``IntegrationRegistry`` iteration) through :class:`RegistryRepositoryFacts`. Rules depend only
on the narrow :class:`RepositoryFacts` protocol, so tests inject synthetic facts.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from ddev.cli.ci.tests.batching.git import ChangedFile, ChangeType

if TYPE_CHECKING:
    from ddev.repo.core import IntegrationRegistry

AGENT_REQUIREMENTS_FILE = "agent_requirements.in"

NON_TESTABLE_FILES = frozenset({"auto_conf.yaml"})

# Integrations ddev still considers testable (they have a `hatch.toml`) but that CI no longer
# runs. This is CI policy layered on top of ddev's `is_testable`, which does not encode it.
UNTESTABLE_TARGETS = frozenset({"mesos_slave"})

# Paths within a target that, when changed, warrant running that target's tests.
TESTABLE_PATH_PATTERN = re.compile(
    r"""
    assets/configuration/.+
  | tests/.+
  | [^/]+\.py
  | hatch\.toml
  | metadata\.csv
  | pyproject\.toml
  | datadog_checks/[^/]+/data/metrics\.yaml
  | datadog_checks/snmp/data/default_profiles/.+
  | datadog_checks/dev/tooling/templates/configuration/.+yaml
    """,
    re.VERBOSE,
)

# Repository-wide paths that, when changed, trigger the full eligible target set.
#
# TODO(manifest): these repository-wide triggers are hard-coded here as path patterns. Once ddev's
# dependency on `manifest.json` is removed and replaced by per-integration tooling configuration,
# the intent is to move this policy there: each integration would declare, as structured config,
# what changes trigger *its own* tests and what (if anything) triggers the full repository test
# set — rather than expressing it as a shared regex string in this module.
REPOSITORY_WIDE_PATTERNS = re.compile(
    r"""
    # Shared testing framework: a change here can affect every integration's tests.
    datadog_checks_base/datadog_checks/.+
  | datadog_checks_dev/datadog_checks/dev/[^/]+\.py
    # ddev test-planning/execution code: target discovery, Hatch environment resolution, unit/E2E
    # invocation, and Dispatcher batching. A change here can alter how *every* target's tests are
    # selected, planned, or run, so it retests the full eligible set. Unrelated ddev tooling (for
    # example `ddev/src/ddev/cli/port_commit.py`) is intentionally not listed and only selects the
    # `ddev` target through the direct rule.
  | ddev/src/ddev/cli/test/.+
  | ddev/src/ddev/cli/env/test\.py
  | ddev/src/ddev/testing/.+
  | ddev/src/ddev/utils/hatch\.py
  | ddev/src/ddev/cli/ci/tests/.+
  | ddev/src/ddev/integration/core\.py
  | ddev/src/ddev/repo/core\.py
    """,
    re.VERBOSE,
)


class RepositoryFacts(Protocol):
    """Narrow read-only view of the repository used by target rules."""

    def is_testable_target(self, name: str) -> bool: ...

    def eligible_targets(self) -> list[str]: ...


@dataclass(frozen=True, eq=False)
class RegistryRepositoryFacts:
    """A :class:`RepositoryFacts` implementation backed by ddev's integration registry.

    Testability is delegated to ddev (``Integration.is_testable`` and
    ``IntegrationRegistry.iter_testable``) so it never diverges from the rest of ddev; the
    only extra policy applied is :data:`UNTESTABLE_TARGETS`.
    """

    registry: IntegrationRegistry

    def is_testable_target(self, name: str) -> bool:
        if name in UNTESTABLE_TARGETS:
            return False
        try:
            return self.registry.get(name).is_testable
        except OSError:
            return False

    def eligible_targets(self) -> list[str]:
        return sorted(
            integration.name
            for integration in self.registry.iter_testable()
            if integration.name not in UNTESTABLE_TARGETS
        )


class TargetRule(Protocol):
    """A behavior that maps changed files to affected target names."""

    def __call__(self, changed_files: Sequence[ChangedFile], facts: RepositoryFacts) -> Iterable[str]: ...


@dataclass(frozen=True)
class DirectTargetRule:
    """Recognize every directly modified testable target in the change set.

    A rename affects both the source and destination targets (a file leaving a target still
    changes that target), while a copy only affects the destination since the source is left
    untouched.
    """

    testable_pattern: re.Pattern[str] = TESTABLE_PATH_PATTERN
    non_testable_files: frozenset[str] = NON_TESTABLE_FILES

    def __call__(self, changed_files: Sequence[ChangedFile], facts: RepositoryFacts) -> Iterator[str]:
        for changed_file in changed_files:
            for path in self._affected_paths(changed_file):
                target = self._target_for_path(path, facts)
                if target is not None:
                    yield target

    @staticmethod
    def _affected_paths(changed_file: ChangedFile) -> list[str]:
        paths = [changed_file.path]
        # A rename removes the file from its source location, so the source target is affected
        # too. A copy leaves the source untouched, so only the destination path matters.
        if changed_file.change_type is ChangeType.RENAMED and changed_file.previous_path is not None:
            paths.append(changed_file.previous_path)
        return paths

    def _target_for_path(self, path: str, facts: RepositoryFacts) -> str | None:
        directory, separator, remaining = path.partition("/")
        if not separator or not remaining:
            return None
        if not facts.is_testable_target(directory):
            return None
        if remaining.rsplit("/", 1)[-1] in self.non_testable_files:
            return None
        if self.testable_pattern.search(remaining):
            return directory
        return None


@dataclass(frozen=True)
class RepositoryWideRule:
    """Trigger the full eligible target set when a repository-wide path changes.

    The repository-wide paths only exist in the core repository, so ``is_core`` gates the
    rule: elsewhere it yields nothing. ``is_core`` is required so a rule can never be built
    without stating which repository it applies to.
    """

    is_core: bool
    patterns: re.Pattern[str] = REPOSITORY_WIDE_PATTERNS
    exempt_files: frozenset[str] = field(default_factory=lambda: frozenset({AGENT_REQUIREMENTS_FILE}))

    def __call__(self, changed_files: Sequence[ChangedFile], facts: RepositoryFacts) -> Iterator[str]:
        if not self.is_core:
            return

        paths = [changed_file.path for changed_file in changed_files]
        if any(path in self.exempt_files for path in paths):
            return
        if any(self.patterns.search(path) for path in paths):
            yield from facts.eligible_targets()


def default_target_rules(*, is_core: bool) -> tuple[TargetRule, ...]:
    """Build the default ordered rule set for a repository."""
    return (DirectTargetRule(), RepositoryWideRule(is_core=is_core))


def find_affected_targets(
    changed_files: Sequence[ChangedFile],
    facts: RepositoryFacts,
    *,
    rules: Sequence[TargetRule],
) -> list[str]:
    """Combine rule results by deterministic ordered union under the testability policy."""
    union: dict[str, None] = {}
    for rule in rules:
        for target in rule(changed_files, facts):
            if facts.is_testable_target(target):
                union.setdefault(target, None)

    return list(union)
