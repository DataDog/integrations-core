# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Static Hatch environment discovery for Dispatcher planning."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.cli.ci.tests.batching.units import ResolvedEnvironment
from ddev.e2e.agent_images import PYTHON_VERSION_PATTERN

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import Any

    from ddev.integration.core import Integration
    from ddev.utils.platform import PlatformName

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


@dataclass(frozen=True)
class HatchEnvironmentSettings:
    e2e_available: bool
    platform_restrictions: list[str]
    # Matrix `os` value -> eligible execution platforms; None means no explicit mapping.
    os_platforms: dict[str, list[str]] | None

    def platforms_for(self, platforms: Sequence[PlatformName], os_name: str | None, field: str) -> list[PlatformName]:
        allowed = self.platform_restrictions
        if os_name is not None:
            if self.os_platforms is None:
                if allowed and os_name not in allowed:
                    return []
                allowed = [os_name]
            elif os_name not in self.os_platforms:
                raise ValueError(f"{field}.os: no platform mapping for {os_name!r}")
            else:
                allowed = self.os_platforms[os_name]
        elif self.os_platforms is not None:
            raise ValueError(f"{field}: matrix.os.platforms requires an os variable")
        return [platform for platform in platforms if not allowed or str(platform) in allowed]


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
        settings = _execution_settings(default)

        result: list[ResolvedEnvironment] = []
        names: set[str] = set()
        for field, variables in _matrix_combinations(default.get("matrix", [])):
            version = _python_version(variables.get("python", python), f"{field}.python")
            name = _environment_name(variables, field)
            if name in names:
                raise ValueError(f"{field}: duplicate environment name {name!r}")
            names.add(name)

            result.extend(
                ResolvedEnvironment(
                    name=name,
                    platform=platform,
                    python_version=version,
                    test_available=True,
                    e2e_available=settings.e2e_available,
                )
                for platform in settings.platforms_for(platforms, variables.get("os"), field)
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


def _execution_settings(default: dict[str, Any]) -> HatchEnvironmentSettings:
    restrictions = _strings(default.get("platforms", []), "envs.default.platforms")
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

    if os_platforms is not None and restrictions:
        raise ValueError("envs.default.platforms: combining literal and matrix platform restrictions is unsupported")
    return HatchEnvironmentSettings(
        e2e_available=availability["e2e-env"], platform_restrictions=restrictions, os_platforms=os_platforms
    )


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
