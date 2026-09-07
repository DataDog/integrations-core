# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Public entry points that turn changed files into test units and batches."""

from __future__ import annotations

import logging
import re
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
    from collections.abc import Iterator, Sequence
    from typing import Any

    from ddev.cli.ci.tests.batching.targets import TargetRule
    from ddev.cli.ci.tests.batching.units import EnvironmentProvider
    from ddev.cli.ci.tests.dispatcher_config import BatchingConfig
    from ddev.cli.ci.tests.messages import BatchJob
    from ddev.integration.core import Integration
    from ddev.repo.core import Repository
    from ddev.utils.git import ChangedFile
    from ddev.utils.platform import PlatformName

logger = logging.getLogger(__name__)

ENVIRONMENT_NAME_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
SUPPORTED_ENVIRONMENT_COLLECTORS = frozenset({"default", "datadog-checks"})
SUPPORTED_OVERRIDE_SCOPES = frozenset({"platform", "env", "matrix", "name"})
UNSUPPORTED_ENVIRONMENT_FIELDS = {
    "default": ("template", "matrix-name-format", "matrix-exclude", "matrix-include"),
    "named": ("template",),
}
UNSUPPORTED_OVERRIDE_FIELDS = frozenset({"python", "platforms", "matrix", "template", "matrix-name-format", "test-env"})
OS_PLATFORM_OVERRIDE = ("matrix", "os", "platforms")
PLATFORM_MAPPING_FIELDS = frozenset({"value", "if"})

# The datadog-checks collector enables both stages on the default environment.
TEST_STAGE_DEFAULTS = {"test-env": True, "e2e-env": True}


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


@dataclass(frozen=True, eq=False)
class HatchEnvironmentProvider:
    """Read candidate environments from Hatch configuration without evaluating project code.

    Parse hatch.toml with tomllib and expand each default matrix into the
    Cartesian product of its axes, with Python first in environment names.
    For example, python = ["3.12", "3.13"] and version = ["1", "2"] produce
    py3.12-1, py3.12-2, py3.13-1, and py3.13-2.

    Each combination produces a candidate per compatible requested platform.
    Without a matrix, use the default environment.

    The test-env flag defaults to true and cannot be disabled or overridden.
    E2E availability uses its literal value (true by default); an e2e-env
    override keeps E2E enabled for the worker to decide.
    Only literal matrix.os.platforms mappings are resolved during planning.
    Unsupported discovery overrides raise a planning error; runtime-only
    settings are ignored.
    """

    default_python_version: str

    def __call__(self, integration: Integration, platforms: Sequence[PlatformName]) -> list[ResolvedEnvironment]:
        import tomllib

        try:
            with open(integration.path / "hatch.toml", "rb") as stream:
                config = tomllib.load(stream)
            return self._resolve(config, platforms)
        except (OSError, ValueError) as error:
            raise PlanningError(f"{integration.name}/hatch.toml: {error}") from error

    def _resolve(self, config: dict[str, Any], platforms: Sequence[PlatformName]) -> list[ResolvedEnvironment]:
        default = _default_environment(config)
        python = _python_version(default.get("python", self.default_python_version), "envs.default.python")
        restrictions = _strings(default.get("platforms", []), "envs.default.platforms")
        availability, os_platforms = _execution_settings(default)
        if os_platforms is not None and restrictions:
            raise ValueError(
                "envs.default.platforms: combining literal and matrix platform restrictions is unsupported"
            )

        result: list[ResolvedEnvironment] = []
        names: set[str] = set()
        for field, variables in _matrix_combinations(default.get("matrix", [])):
            version = _python_version(variables.get("python", python), f"{field}.python")
            name = _environment_name(variables, field)
            if name in names:
                raise ValueError(f"{field}: duplicate environment name {name!r}")
            names.add(name)

            candidates = _environment_platforms(platforms, variables.get("os"), restrictions, os_platforms, field)
            result.extend(
                ResolvedEnvironment(
                    name=name,
                    platform=platform,
                    python_version=version,
                    test_available=availability["test-env"],
                    e2e_available=availability["e2e-env"],
                )
                for platform in candidates
            )
        return result


def _default_environment(config: dict[str, Any]) -> dict[str, Any]:
    env = _table(config.get("env", {}), "env")
    collectors = _table(env.get("collectors", {}), "env.collectors")
    if unknown := collectors.keys() - SUPPORTED_ENVIRONMENT_COLLECTORS:
        raise ValueError(f"env.collectors: unsupported collectors {sorted(unknown)}")

    envs = _table(config.get("envs", {}), "envs")
    for name, value in envs.items():
        if name == "default":
            continue
        named = _table(value, f"envs.{name}")
        for field in UNSUPPORTED_ENVIRONMENT_FIELDS["named"]:
            if field in named:
                raise ValueError(f"envs.{name}.{field}: unsupported for static discovery")
        if any(named.get(field, False) for field in TEST_STAGE_DEFAULTS):
            raise ValueError(f"envs.{name}: test environments outside envs.default are unsupported")
        for _, _, settings in _overrides(named.get("overrides", {}), f"envs.{name}.overrides"):
            if settings.keys() & TEST_STAGE_DEFAULTS.keys():
                raise ValueError(f"envs.{name}.overrides: conditional named test environments are unsupported")

    default = _table(envs.get("default", {}), "envs.default")
    for field in UNSUPPORTED_ENVIRONMENT_FIELDS["default"]:
        if field in default:
            raise ValueError(f"envs.default.{field}: unsupported for static discovery")
    if default.get("type", "virtual") != "virtual":
        raise ValueError("envs.default.type: only virtual environments support static discovery")
    return default


def _execution_settings(default: dict[str, Any]) -> tuple[dict[str, bool], dict[str, list[str]] | None]:
    availability = {}
    for field, fallback in TEST_STAGE_DEFAULTS.items():
        value = default.get(field, fallback)
        if not isinstance(value, bool):
            raise ValueError(f"envs.default.{field}: expected a boolean")
        availability[field] = value
    if not availability["test-env"]:
        raise ValueError("envs.default.test-env: disabling unit tests is unsupported for static discovery")

    os_platforms = None
    for scope, selector, settings in _overrides(default.get("overrides", {}), "envs.default.overrides"):
        for field, value in settings.items():
            location = f"envs.default.overrides.{scope}.{selector}.{field}"
            if (scope, selector, field) == OS_PLATFORM_OVERRIDE:
                os_platforms = _os_platform_mapping(value, location)
            elif field in UNSUPPORTED_OVERRIDE_FIELDS:
                raise ValueError(f"{location}: unsupported for static discovery")
            elif field == "e2e-env":
                # ddev env test evaluates E2E availability on the worker.
                availability[field] = True
    return availability, os_platforms


def _matrix_combinations(value: object) -> Iterator[tuple[str, dict[str, str]]]:
    from itertools import product

    if not isinstance(value, list):
        raise ValueError("envs.default.matrix: expected an array of tables")
    for index, entry in enumerate(value or [{}]):
        field = f"envs.default.matrix[{index}]"
        matrix = _table(entry, field)
        if value and not matrix:
            raise ValueError(f"{field}: expected at least one matrix variable")
        # Hatch places Python first in environment names, regardless of TOML key order.
        axes = sorted(matrix, key=lambda key: key != "python")
        values = [_strings(matrix[axis], f"{field}.{axis}", nonempty=True) for axis in axes]
        for combination in product(*values):
            yield field, dict(zip(axes, combination, strict=True))


def _environment_name(variables: dict[str, str], field: str) -> str:
    name = "-".join(f"py{value}" if key == "python" else value for key, value in variables.items()) or "default"
    if not ENVIRONMENT_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"{field}: invalid environment name {name!r}")
    return name


def _environment_platforms(
    platforms: Sequence[PlatformName],
    os_name: str | None,
    restrictions: list[str],
    os_platforms: dict[str, list[str]] | None,
    field: str,
) -> list[PlatformName]:
    allowed = restrictions
    if os_name is not None:
        if os_platforms is None:
            if restrictions and os_name not in restrictions:
                return []
            allowed = [os_name]
        elif os_name not in os_platforms:
            raise ValueError(f"{field}.os: no platform mapping for {os_name!r}")
        else:
            allowed = os_platforms[os_name]
    elif os_platforms is not None:
        raise ValueError(f"{field}: matrix.os.platforms requires an os variable")
    return [platform for platform in platforms if not allowed or str(platform) in allowed]


def _table(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected a table")
    return value


def _strings(value: object, field: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{field}: expected an array of nonempty strings")
    if nonempty and not value:
        raise ValueError(f"{field}: expected at least one value")
    return value


def _python_version(value: object, field: str) -> str:
    if not isinstance(value, str) or not PYTHON_VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"{field}: expected a `major.minor` Python version, got {value!r}")
    return value


def _overrides(value: object, field: str) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for scope, selectors in _table(value, field).items():
        if scope not in SUPPORTED_OVERRIDE_SCOPES:
            continue
        for selector, settings in _table(selectors, f"{field}.{scope}").items():
            yield scope, selector, _table(settings, f"{field}.{scope}.{selector}")


def _os_platform_mapping(value: object, field: str) -> dict[str, list[str]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field}: expected literal value/if mappings")
    platforms: dict[str, list[str]] = {}
    for item in value:
        mapping = _table(item, field)
        if mapping.keys() != PLATFORM_MAPPING_FIELDS or not isinstance(mapping["value"], str) or not mapping["value"]:
            raise ValueError(f"{field}: only literal value/if mappings are supported")
        for os_name in _strings(mapping["if"], f"{field}.if", nonempty=True):
            platforms.setdefault(os_name, []).append(mapping["value"])
    return platforms
