# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import ast
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

LabelCategory = Literal["reserved", "generic", "unbounded"]
RESERVED_LABELS = frozenset({"device", "env", "host", "service", "source", "team", "version"})
GENERIC_LABELS = frozenset({"component", "id", "name", "role", "state", "status", "type"})
UNBOUNDED_LABELS = frozenset({"request_id", "trace_id"})
LABEL_CATEGORIES: dict[str, LabelCategory] = {
    **dict.fromkeys(RESERVED_LABELS, "reserved"),
    **dict.fromkeys(GENERIC_LABELS, "generic"),
    **dict.fromkeys(UNBOUNDED_LABELS, "unbounded"),
}
UNRESOLVED = object()


class LabelHygieneError(Exception):
    """Raised when authoritative inputs cannot be read or interpreted."""


@dataclass(frozen=True)
class LabelHygieneIssue:
    """A protected source label that is not safely renamed or excluded."""

    label: str
    category: LabelCategory
    metric_families: tuple[str, ...]
    invalid_target: str | None = None


@dataclass(frozen=True)
class LabelHygieneResult:
    """The complete label-hygiene verdict for one generated check."""

    issues: tuple[LabelHygieneIssue, ...]
    config_error: str | None = None

    @property
    def valid(self) -> bool:
        return not self.issues and self.config_error is None

    def failure_reason(self, check_path: Path) -> str | None:
        """Render an actionable worker diagnostic, or ``None`` when validation passed."""
        if self.valid:
            return None

        lines = ["OpenMetrics label hygiene validation failed."]
        if self.config_error is not None:
            lines.append(f"- Could not verify `{check_path}`: {self.config_error}")
        for issue in self.issues:
            families = ", ".join(f"`{name}`" for name in issue.metric_families)
            if self.config_error is not None:
                problem = "requires verifiable handling"
            elif issue.invalid_target is None:
                problem = "is not renamed or excluded"
            else:
                problem = f"is renamed to `{issue.invalid_target}`, which is also a protected label"
            lines.append(f"- `{issue.label}` ({issue.category}) {problem}; exposed by metric families: {families}.")
        lines.append(
            "Handle every listed source label in `get_default_config()` using a product-specific "
            "`rename_labels` target or `exclude_labels`."
        )
        return "\n".join(lines)


def lint_label_hygiene(catalog_paths: Sequence[Path], check_path: Path) -> LabelHygieneResult:
    """Compare protected catalog labels with the generated check's declarative handling."""
    occurrences = _load_protected_label_occurrences(catalog_paths)
    if not occurrences:
        return LabelHygieneResult(issues=())

    try:
        rename_labels, exclude_labels = _extract_label_handling(check_path)
    except LabelHygieneError as e:
        return LabelHygieneResult(issues=_unhandled_issues(occurrences), config_error=str(e))

    issues: list[LabelHygieneIssue] = []
    for label, metric_families in sorted(occurrences.items()):
        if label in exclude_labels:
            continue
        target = rename_labels.get(label)
        if target is not None and target not in LABEL_CATEGORIES:
            continue
        issues.append(
            LabelHygieneIssue(
                label=label,
                category=LABEL_CATEGORIES[label],
                metric_families=tuple(sorted(metric_families)),
                invalid_target=target,
            )
        )
    return LabelHygieneResult(issues=tuple(issues))


def _unhandled_issues(occurrences: dict[str, set[str]]) -> tuple[LabelHygieneIssue, ...]:
    """Convert catalog occurrences into stable issues when config handling is unknown."""
    return tuple(
        LabelHygieneIssue(
            label=label,
            category=LABEL_CATEGORIES[label],
            metric_families=tuple(sorted(metric_families)),
        )
        for label, metric_families in sorted(occurrences.items())
    )


def _load_protected_label_occurrences(catalog_paths: Sequence[Path]) -> dict[str, set[str]]:
    """Collect protected labels and every metric family exposing them across all catalogs.

    The first JSONL row is provenance rather than a metric and is skipped when both
    ``name`` and ``label_keys`` are absent. Metric rows are validated strictly because
    incomplete catalog data would make a passing hygiene verdict unreliable.
    """
    occurrences: dict[str, set[str]] = {}
    for path in catalog_paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            raise LabelHygieneError(f"Failed to read metrics catalog {path}: {e}") from e

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise LabelHygieneError(f"Invalid JSON in metrics catalog {path}:{line_number}: {e}") from e
            if not isinstance(row, dict):
                raise LabelHygieneError(f"Expected an object in metrics catalog {path}:{line_number}")

            metric_name = row.get("name")
            label_keys = row.get("label_keys")
            if metric_name is None and label_keys is None:
                continue
            if (
                not isinstance(metric_name, str)
                or not isinstance(label_keys, list)
                or not all(isinstance(label, str) for label in label_keys)
            ):
                raise LabelHygieneError(f"Invalid metric row in metrics catalog {path}:{line_number}")
            for label in label_keys:
                if label in LABEL_CATEGORIES:
                    occurrences.setdefault(label, set()).add(metric_name)
    return occurrences


def _extract_label_handling(check_path: Path) -> tuple[dict[str, str], set[str]]:
    """Statically read ``rename_labels`` and ``exclude_labels`` from the generated check.

    Generated integration code is deliberately never imported or executed. Instead, the
    method evaluates the limited declarative Python shapes supported by
    ``_evaluate_static_value`` and rejects code whose effective configuration cannot be
    proven from its syntax. It returns the source-to-target ``rename_labels`` mapping and
    the set of source labels named by ``exclude_labels``, in that order.
    """
    try:
        source = check_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise LabelHygieneError(f"Generated check does not exist at the expected path: {check_path}") from e
    except OSError as e:
        raise LabelHygieneError(f"Failed to read generated check: {e}") from e
    try:
        module = ast.parse(source, filename=str(check_path))
    except SyntaxError as e:
        raise LabelHygieneError(f"Generated check is not valid Python: {e.msg} (line {e.lineno})") from e

    function = next(
        (node for node in ast.walk(module) if isinstance(node, ast.FunctionDef) and node.name == "get_default_config"),
        None,
    )
    if function is None:
        raise LabelHygieneError("`get_default_config()` is missing")

    values = _collect_assignments(module.body)
    return_index = -1
    return_node: ast.Return | None = None
    for index, statement in enumerate(function.body):
        if isinstance(statement, ast.Return):
            return_index = index
            return_node = statement
            break
    if return_node is None or return_node.value is None:
        raise LabelHygieneError("`get_default_config()` does not return a configuration dictionary")
    values.update(_collect_assignments(function.body[:return_index]))

    config = _evaluate_static_value(return_node.value, values, set())
    if not isinstance(config, dict):
        raise LabelHygieneError("`get_default_config()` must return a statically readable dictionary")

    rename_labels = _string_mapping(config.get("rename_labels", {}), "rename_labels")
    exclude_labels = _string_set(config.get("exclude_labels", ()), "exclude_labels")
    return rename_labels, exclude_labels


def _collect_assignments(statements: Sequence[ast.stmt]) -> dict[str, ast.expr]:
    """Index simple name assignments for later static expression resolution."""
    values: dict[str, ast.expr] = {}
    for statement in statements:
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            values[statement.targets[0].id] = statement.value
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.value is not None
        ):
            values[statement.target.id] = statement.value
    return values


def _evaluate_static_value(node: ast.expr, values: dict[str, ast.expr], resolving: set[str]) -> object:
    """Evaluate safe declarative AST expressions without running generated code.

    Supported forms cover literals, named constants, containers, dictionary unpacking
    and union, ``dict(...)`` keyword construction, and dictionary ``copy()``. Unknown
    expressions return ``UNRESOLVED``; ``resolving`` prevents cycles between names.
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in resolving or node.id not in values:
            return UNRESOLVED
        return _evaluate_static_value(values[node.id], values, {*resolving, node.id})
    if isinstance(node, ast.Dict):
        result: dict[object, object] = {}
        for key_node, value_node in zip(node.keys, node.values, strict=True):
            if key_node is None:
                unpacked = _evaluate_static_value(value_node, values, resolving)
                if not isinstance(unpacked, dict):
                    return UNRESOLVED
                result.update(unpacked)
                continue
            key = _evaluate_static_value(key_node, values, resolving)
            if key is UNRESOLVED:
                return UNRESOLVED
            try:
                result[key] = _evaluate_static_value(value_node, values, resolving)
            except TypeError:
                return UNRESOLVED
        return result
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        items = [_evaluate_static_value(element, values, resolving) for element in node.elts]
        if isinstance(node, ast.List):
            return items
        if isinstance(node, ast.Tuple):
            return tuple(items)
        try:
            return set(items)
        except TypeError:
            return UNRESOLVED
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _evaluate_static_value(node.left, values, resolving)
        right = _evaluate_static_value(node.right, values, resolving)
        if isinstance(left, dict) and isinstance(right, dict):
            return left | right
        return UNRESOLVED
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" and not node.args:
        if any(keyword.arg is None for keyword in node.keywords):
            return UNRESOLVED
        return {keyword.arg: _evaluate_static_value(keyword.value, values, resolving) for keyword in node.keywords}
    if (
        isinstance(node, ast.Call)
        and not node.args
        and not node.keywords
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "copy"
    ):
        copied = _evaluate_static_value(node.func.value, values, resolving)
        return copied.copy() if isinstance(copied, dict) else UNRESOLVED
    return UNRESOLVED


def _string_mapping(value: object, name: str) -> dict[str, str]:
    """Require a statically resolved string-to-string configuration mapping."""
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise LabelHygieneError(f"`{name}` must be a statically readable string-to-string dictionary")
    return cast(dict[str, str], value)


def _string_set(value: object, name: str) -> set[str]:
    """Require a statically resolved collection of string label names."""
    if not isinstance(value, (list, tuple, set)) or not all(isinstance(item, str) for item in value):
        raise LabelHygieneError(f"`{name}` must be a statically readable collection of strings")
    return set(value)
