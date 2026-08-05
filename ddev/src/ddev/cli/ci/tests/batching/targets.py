# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Discovery of the targets a change set affects, as a composition of independent rules."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from ddev.utils.git import ChangedFile

if TYPE_CHECKING:
    from ddev.repo.core import IntegrationRegistry

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
# Deliberately narrower than the `paths` filter of `.github/workflows/pr-all.yml`, which also
# triggers on `ddev/src/**`, the tooling `pyproject.toml` files, and the workflow definitions.
# Whether Dispatcher should match those too is still an open decision.
#
# TODO(manifest): once ddev no longer depends on `manifest.json`, each integration should declare
# its own triggers as structured configuration instead of this shared regex.
REPOSITORY_WIDE_PATTERNS = re.compile(
    r"""
    # Shared testing framework.
    datadog_checks_base/datadog_checks/.+
  | datadog_checks_dev/datadog_checks/dev/[^/]+\.py
    # ddev's test planning and execution code. Other ddev tooling is intentionally absent and only
    # selects the `ddev` target through the direct rule.
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
    """`RepositoryFacts` backed by ddev's integration registry, plus the `UNTESTABLE_TARGETS` policy."""

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

    Each change is matched against every path it affects, so a rename selects both the target it
    left and the one it landed in.
    """

    testable_pattern: re.Pattern[str] = TESTABLE_PATH_PATTERN
    non_testable_files: frozenset[str] = NON_TESTABLE_FILES

    def __call__(self, changed_files: Sequence[ChangedFile], facts: RepositoryFacts) -> Iterator[str]:
        for changed_file in changed_files:
            for path in changed_file.affected_paths:
                target = self._target_for_path(path, facts)
                if target is not None:
                    yield target

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

    Those paths only exist in the core repository, so the rule yields nothing elsewhere. `is_core`
    is required rather than defaulted so a rule can never be built without stating where it applies.
    """

    is_core: bool
    patterns: re.Pattern[str] = REPOSITORY_WIDE_PATTERNS

    def __call__(self, changed_files: Sequence[ChangedFile], facts: RepositoryFacts) -> Iterator[str]:
        if not self.is_core:
            return

        if any(self.patterns.search(changed_file.path) for changed_file in changed_files):
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
    """Combine every rule's results into the unique set of testable targets.

    Deduplication is what matters: a target selected by two rules would otherwise plan two
    identically named jobs. The dict keeps insertion order on top of that, which costs nothing
    over a set and makes runs comparable when debugging, but nothing downstream depends on it.
    """
    union: dict[str, None] = {}
    for rule in rules:
        for target in rule(changed_files, facts):
            if facts.is_testable_target(target):
                union.setdefault(target, None)

    return list(union)
