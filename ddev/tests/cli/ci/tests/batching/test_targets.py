# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass

import pytest

from ddev.cli.ci.tests.batching.git import ChangedFile, ChangeType
from ddev.cli.ci.tests.batching.targets import (
    UNTESTABLE_TARGETS,
    DirectTargetRule,
    RegistryRepositoryFacts,
    RepositoryWideRule,
    default_target_rules,
    find_affected_targets,
)

CORE_RULES = default_target_rules(is_core=True)


@dataclass(frozen=True)
class FakeRepositoryFacts:
    """Test-only ``RepositoryFacts`` backed by a fixed target set.

    Production code sources testability from ddev via ``RegistryRepositoryFacts``; this synthetic
    implementation lets rule tests inject a known set of testable targets without a real registry.
    It mirrors the same ``UNTESTABLE_TARGETS`` CI policy the registry-backed facts apply.
    """

    testable_targets: frozenset[str]

    def is_testable_target(self, name: str) -> bool:
        return name not in UNTESTABLE_TARGETS and name in self.testable_targets

    def eligible_targets(self) -> list[str]:
        return sorted(name for name in self.testable_targets if name not in UNTESTABLE_TARGETS)


def modified(path: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.MODIFIED, path=path)


def renamed(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.RENAMED, path=destination, previous_path=source)


def copied(source: str, destination: str) -> ChangedFile:
    return ChangedFile(change_type=ChangeType.COPIED, path=destination, previous_path=source)


def facts(*targets: str) -> FakeRepositoryFacts:
    return FakeRepositoryFacts(testable_targets=frozenset(targets))


def test_direct_rule_recognizes_modified_testable_target():
    changed = [modified("postgres/datadog_checks/postgres/check.py")]

    assert list(DirectTargetRule()(changed, facts("postgres"))) == ["postgres"]


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("postgres/README.md", id="non-testable-path"),
        pytest.param("postgres/auto_conf.yaml", id="non-testable-file"),
        pytest.param("some_dir/foo.py", id="not-a-target"),
    ],
)
def test_direct_rule_ignores(path):
    changed = [modified(path)]

    assert list(DirectTargetRule()(changed, facts("postgres"))) == []


def test_direct_rule_multiple_integrations_all_returned():
    changed = [
        modified("postgres/tests/test_a.py"),
        modified("postgres/pyproject.toml"),
        modified("mysql/tests/test_b.py"),
    ]

    assert list(DirectTargetRule()(changed, facts("postgres", "mysql"))) == ["postgres", "postgres", "mysql"]


def test_direct_rule_rename_out_of_target_affects_source():
    # A test file renamed out of postgres into a non-target directory still changes postgres.
    changed = [renamed("postgres/tests/test_a.py", "docs/moved_test.py")]

    assert list(DirectTargetRule()(changed, facts("postgres"))) == ["postgres"]


def test_direct_rule_rename_between_targets_affects_both():
    changed = [renamed("postgres/tests/test_a.py", "mysql/tests/test_a.py")]

    # Destination (path) is yielded before source (previous_path).
    assert list(DirectTargetRule()(changed, facts("postgres", "mysql"))) == ["mysql", "postgres"]


def test_direct_rule_copy_affects_only_destination():
    changed = [copied("postgres/tests/test_a.py", "mysql/tests/test_a.py")]

    assert list(DirectTargetRule()(changed, facts("postgres", "mysql"))) == ["mysql"]


def test_repository_wide_rule_triggers_full_eligible_set_in_core():
    rule = RepositoryWideRule(is_core=True)
    changed = [modified("datadog_checks_base/datadog_checks/base/utils/foo.py")]

    assert list(rule(changed, facts("postgres", "mysql", "datadog_checks_base"))) == [
        "datadog_checks_base",
        "mysql",
        "postgres",
    ]


def test_repository_wide_rule_ignores_when_only_exempt_file_changed():
    rule = RepositoryWideRule(is_core=True)
    changed = [
        modified("agent_requirements.in"),
        modified("datadog_checks_base/datadog_checks/base/utils/foo.py"),
    ]

    assert list(rule(changed, facts("postgres", "datadog_checks_base"))) == []


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("ddev/src/ddev/cli/test/__init__.py", id="unit-test-invocation"),
        pytest.param("ddev/src/ddev/cli/env/test.py", id="e2e-test-invocation"),
        pytest.param("ddev/src/ddev/testing/constants.py", id="testing-constants"),
        pytest.param("ddev/src/ddev/utils/hatch.py", id="hatch-environment-resolution"),
        pytest.param("ddev/src/ddev/cli/ci/tests/batching/units.py", id="dispatcher-planning"),
        pytest.param("ddev/src/ddev/cli/ci/tests/task_test_runner.py", id="dispatcher-execution"),
        pytest.param("ddev/src/ddev/cli/ci/tests/task_test_gatherer.py", id="dispatcher-reporting"),
        pytest.param("ddev/src/ddev/cli/ci/tests/messages.py", id="dispatcher-messages"),
        pytest.param("ddev/src/ddev/integration/core.py", id="integration-model"),
        pytest.param("ddev/src/ddev/repo/core.py", id="repository-model"),
    ],
)
def test_repository_wide_rule_triggers_full_set_for_ddev_test_planning_paths(path):
    # A change to ddev code that governs how tests are discovered/planned/run retests everything.
    rule = RepositoryWideRule(is_core=True)
    changed = [modified(path)]

    assert list(rule(changed, facts("postgres", "mysql", "ddev"))) == ["ddev", "mysql", "postgres"]


def test_repository_wide_rule_ignores_unrelated_ddev_tooling():
    # An unrelated ddev command is not a test-planning path, so it does not trigger the full set.
    rule = RepositoryWideRule(is_core=True)
    changed = [modified("ddev/src/ddev/cli/port_commit.py")]

    assert list(rule(changed, facts("postgres", "mysql", "ddev"))) == []


def test_find_affected_targets_unrelated_ddev_command_selects_only_ddev():
    # End to end: changing an unrelated ddev command selects only the `ddev` target (via the direct
    # rule), never the whole repository.
    changed = [modified("ddev/src/ddev/cli/port_commit.py")]

    assert find_affected_targets(changed, facts("postgres", "mysql", "ddev"), rules=CORE_RULES) == ["ddev"]


def test_find_affected_targets_ddev_test_planning_change_triggers_full_set():
    # End to end: changing ddev's Hatch environment resolution retests every eligible target.
    changed = [modified("ddev/src/ddev/utils/hatch.py")]

    assert find_affected_targets(changed, facts("postgres", "mysql", "ddev"), rules=CORE_RULES) == [
        "ddev",
        "mysql",
        "postgres",
    ]


def test_repository_wide_rule_does_not_fire_outside_core():
    rule = RepositoryWideRule(is_core=False)
    changed = [modified("datadog_checks_base/datadog_checks/base/utils/foo.py")]

    assert list(rule(changed, facts("postgres", "datadog_checks_base"))) == []


def test_repository_wide_rule_ignores_irrelevant_paths():
    rule = RepositoryWideRule(is_core=True)
    changed = [modified("postgres/tests/test_a.py")]

    assert list(rule(changed, facts("postgres", "datadog_checks_base"))) == []


def test_find_affected_targets_multiple_integrations_ordered_union_no_duplicates():
    changed = [
        modified("postgres/tests/test_a.py"),
        modified("postgres/pyproject.toml"),
        modified("mysql/tests/test_b.py"),
    ]

    assert find_affected_targets(changed, facts("postgres", "mysql"), rules=CORE_RULES) == ["postgres", "mysql"]


def test_find_affected_targets_broad_and_direct_overlap_deduplicated():
    changed = [
        modified("postgres/tests/test_a.py"),
        modified("datadog_checks_base/datadog_checks/base/utils/foo.py"),
    ]

    result = find_affected_targets(changed, facts("postgres", "mysql", "datadog_checks_base"), rules=CORE_RULES)

    # postgres from the direct rule, then the broad rule adds the full eligible set, each once.
    assert result == ["postgres", "datadog_checks_base", "mysql"]


def test_find_affected_targets_irrelevant_paths_yield_nothing():
    changed = [modified("docs/readme.md"), modified(".github/workflows/foo.yml")]

    assert find_affected_targets(changed, facts("postgres", "mysql"), rules=CORE_RULES) == []


def test_find_affected_targets_excludes_untestable_targets():
    # mesos_slave is directly modified but excluded by CI policy, so it never appears.
    changed = [modified("mesos_slave/tests/test_a.py"), modified("postgres/tests/test_a.py")]

    assert find_affected_targets(changed, facts("postgres"), rules=CORE_RULES) == ["postgres"]


def test_default_target_rules_are_direct_then_repository_wide():
    rules = default_target_rules(is_core=False)

    assert isinstance(rules[0], DirectTargetRule)
    assert isinstance(rules[1], RepositoryWideRule)
    assert rules[1].is_core is False


class FakeIntegration:
    def __init__(self, name: str, is_testable: bool):
        self.name = name
        self.is_testable = is_testable


class FakeRegistry:
    """A minimal stand-in for ddev's ``IntegrationRegistry`` (no git repository)."""

    def __init__(self, integrations):
        self._integrations = {integration.name: integration for integration in integrations}

    def get(self, name: str):
        try:
            return self._integrations[name]
        except KeyError:
            raise OSError(f"Integration does not exist: {name}") from None

    def iter_testable(self):
        return [integration for integration in self._integrations.values() if integration.is_testable]


@pytest.mark.parametrize(
    "name, expected",
    [
        pytest.param("postgres", True, id="testable"),
        # mesos_slave is testable per ddev but excluded by CI policy.
        pytest.param("mesos_slave", False, id="untestable-policy"),
        # iis is not testable per ddev (no hatch.toml).
        pytest.param("iis", False, id="not-testable-per-ddev"),
        pytest.param("unknown", False, id="unknown"),
    ],
)
def test_registry_repository_facts_is_testable_target(name, expected):
    registry = FakeRegistry(
        [
            FakeIntegration("postgres", is_testable=True),
            FakeIntegration("mesos_slave", is_testable=True),
            FakeIntegration("iis", is_testable=False),
        ]
    )

    assert RegistryRepositoryFacts(registry).is_testable_target(name) is expected


def test_registry_repository_facts_eligible_targets_excludes_untestable_and_policy():
    registry = FakeRegistry(
        [
            FakeIntegration("postgres", is_testable=True),
            FakeIntegration("mesos_slave", is_testable=True),
            FakeIntegration("iis", is_testable=False),
        ]
    )

    assert RegistryRepositoryFacts(registry).eligible_targets() == ["postgres"]
