# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path

import pytest

from ddev.ai.phases.openmetrics.label_hygiene import LabelHygieneError, lint_label_hygiene


def write_catalog(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"endpoint_name": "api", "endpoint_url": "http://example.test", "exposition_format": "prometheus"},
                *rows,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_check(path: Path, default_config: dict[str, object]) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        f"class ExampleCheck:\n    def get_default_config(self):\n        return {default_config!r}\n",
        encoding="utf-8",
    )


def test_reports_reserved_generic_and_unbounded_labels_with_metric_provenance(tmp_path: Path) -> None:
    catalog = tmp_path / "inspect_endpoint_api_metrics.jsonl"
    check = tmp_path / "example" / "check.py"
    write_catalog(
        catalog,
        [
            {"name": "iris_system_info", "label_keys": ["version", "host"]},
            {"name": "request_state", "label_keys": ["status", "request_id"]},
            {"name": "another_info", "label_keys": ["version"]},
        ],
    )
    write_check(check, {"rename_labels": {"host": "iris_host"}})

    result = lint_label_hygiene([catalog], check)
    reason = result.failure_reason(check)

    assert not result.valid
    assert reason is not None
    assert "`version` (reserved) is not renamed or excluded" in reason
    assert "`iris_system_info`, `another_info`" not in reason
    assert "`another_info`, `iris_system_info`" in reason
    assert "`status` (generic)" in reason
    assert "`request_id` (unbounded)" in reason
    assert "`host`" not in reason


def test_accepts_product_specific_renames_and_exclusions(tmp_path: Path) -> None:
    catalog = tmp_path / "inspect_endpoint_api_metrics.jsonl"
    check = tmp_path / "example" / "check.py"
    write_catalog(
        catalog,
        [{"name": "iris_system_info", "label_keys": ["version", "host", "status", "trace_id"]}],
    )
    check.parent.mkdir(parents=True)
    check.write_text(
        "RENAMES = {'version': 'iris_version'}\n"
        "BASE = {'host': 'iris_host'}\n"
        "class ExampleCheck:\n"
        "    def get_default_config(self):\n"
        "        rename_labels = BASE | RENAMES\n"
        "        return dict(rename_labels=rename_labels, exclude_labels=['status', 'trace_id'])\n",
        encoding="utf-8",
    )

    result = lint_label_hygiene([catalog], check)

    assert result.valid
    assert result.failure_reason(check) is None


def test_rejects_rename_to_another_protected_label(tmp_path: Path) -> None:
    catalog = tmp_path / "inspect_endpoint_api_metrics.jsonl"
    check = tmp_path / "example" / "check.py"
    write_catalog(catalog, [{"name": "iris_system_info", "label_keys": ["version"]}])
    write_check(check, {"rename_labels": {"version": "status"}})

    result = lint_label_hygiene([catalog], check)

    assert not result.valid
    assert result.issues[0].invalid_target == "status"
    assert "also a protected label" in result.failure_reason(check)


def test_passes_without_reading_check_when_catalog_has_no_protected_labels(tmp_path: Path) -> None:
    catalog = tmp_path / "inspect_endpoint_api_metrics.jsonl"
    missing_check = tmp_path / "missing.py"
    write_catalog(catalog, [{"name": "requests", "label_keys": ["method", "route"]}])

    result = lint_label_hygiene([catalog], missing_check)

    assert result.valid


def test_reports_configuration_that_cannot_be_statically_verified(tmp_path: Path) -> None:
    catalog = tmp_path / "inspect_endpoint_api_metrics.jsonl"
    check = tmp_path / "example" / "check.py"
    write_catalog(catalog, [{"name": "iris_system_info", "label_keys": ["version"]}])
    check.parent.mkdir(parents=True)
    check.write_text(
        "class ExampleCheck:\n    def get_default_config(self):\n        return build_config()\n",
        encoding="utf-8",
    )

    result = lint_label_hygiene([catalog], check)

    assert not result.valid
    assert result.config_error is not None
    assert "statically readable dictionary" in result.config_error
    reason = result.failure_reason(check)
    assert reason is not None
    assert "`version` (reserved) requires verifiable handling" in reason
    assert "`iris_system_info`" in reason


@pytest.mark.parametrize(
    "config_expression",
    ["{['unhashable']: 1}", "{'rename_labels': {{'host': 'iris_host'}}}"],
)
def test_unhashable_static_values_are_unverifiable_instead_of_crashing(
    config_expression: str,
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "metrics.jsonl"
    check = tmp_path / "check.py"
    write_catalog(catalog, [{"name": "metric", "label_keys": ["host"]}])
    check.write_text(f"def get_default_config():\n    return {config_expression}\n", encoding="utf-8")

    result = lint_label_hygiene([catalog], check)

    assert not result.valid
    assert result.config_error is not None
    assert "statically readable" in result.config_error


def test_rejects_malformed_catalog(tmp_path: Path) -> None:
    catalog = tmp_path / "inspect_endpoint_api_metrics.jsonl"
    catalog.write_text('{"name": "broken"\n', encoding="utf-8")

    with pytest.raises(LabelHygieneError, match="Invalid JSON"):
        lint_label_hygiene([catalog], tmp_path / "check.py")
