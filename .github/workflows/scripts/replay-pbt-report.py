#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Build sanitized Replay PBT human and machine reports.

This script intentionally emits an allowlisted report bundle. It parses the
small result/finding artifacts produced by Replay PBT jobs, classifies and
summarizes them, and writes a single zip containing only curated report files.
It must not copy arbitrary replay cache, capture, config, or log artifacts.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REDACTED = "<redacted>"
MAX_TEXT = 500
MAX_DETAIL_TEXT = 2000

AUTH_TEXT_RE = re.compile(
    r"(?i)\b(?P<key>authorization|proxy-authorization)\s*[:=]\s*(?P<value>(bearer|basic)?\s*[^\s,;]+)"
)
KEY_VALUE_TEXT_RE = re.compile(
    r"(?i)\b(?P<key>api[_-]?key|app[_-]?key|application[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|secret|password|passwd|passphrase|private[_-]?key|client[_-]?secret|credential|signature|session)\s*[:=]\s*(?P<value>[^\s,;}]+)"
)
PRIVATE_KEY_TEXT_RE = re.compile(r"(?is)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----")
URL_CREDENTIAL_TEXT_RE = re.compile(r"(?i)(https?://)[^\s/@:]+:[^\s/@]+@")

CATEGORY_DEFINITIONS = {
    "passed": ("✅", "Passed", "All replay-PBT properties passed."),
    "failed-before-replay-pbt": ("🧱", "Failed before replay-PBT", "Setup, cache probing/seeding, compare-check, or orchestration failed before property tests ran."),
    "skipped-missing-cache": ("⏭️", "Skipped missing cache", "No suitable replay cache was restored and seeding was disabled."),
    "replay-nondeterminism": ("🧬", "Replay nondeterminism", "Same fixture/ref did not replay deterministically."),
    "openmetrics-mutation": ("🔀", "OpenMetrics mutation mismatch", "A mutated OpenMetrics cache did not preserve check output."),
    "asset-metadata-mismatch": ("📊", "Asset / metadata mismatch", "Dashboard/monitor/service-check assets reference metrics or tags missing from metadata."),
    "metadata-contract": ("📋", "Metadata contract", "metadata.csv and emitted metrics/tags disagree."),
    "coverage": ("📈", "OpenMetrics coverage", "OpenMetrics coverage property failed."),
    "unsupported-negative": ("🚧", "Unsupported or negative fixture", "The target appears intentionally unsupported or uses a negative/error-path fixture."),
    "replay-harness": ("🛠️", "Replay harness", "Replay framework or adapter behavior likely needs work."),
    "other-failed": ("❓", "Other replay-PBT failure", "Failed during replay-PBT but did not match a known category."),
    "unknown": ("❔", "Unknown", "No usable status was reported."),
}

STATUS_DEFINITIONS = {
    "passed": ("✅", "Passed"),
    "failed": ("❌", "Property failure"),
    "failed-before-replay-pbt": ("🧱", "Setup/cache failure"),
    "skipped-missing-cache": ("⏭️", "Skipped: missing cache"),
    "cache-hit": ("✅", "Cache ready"),
    "seeded-cache": ("✅", "Cache seeded"),
}


def status_icon(status: Any) -> str:
    return STATUS_DEFINITIONS.get(str(status or ""), ("❔", "Unknown"))[0]


def status_label(status: Any) -> str:
    text = str(status or "unknown")
    return STATUS_DEFINITIONS.get(text, ("❔", text.replace("-", " ").title()))[1]


PROPERTY_DEFINITIONS = {
    "deterministic": (
        "Determinism",
        "Replay the same cached input twice. The check should emit the same normalized output both times.",
    ),
    "openmetrics-label-order": (
        "OpenMetrics label order",
        "Sort labels inside captured OpenMetrics samples. Label order should not change the emitted metrics.",
    ),
    "openmetrics-comments-blank-lines": (
        "OpenMetrics comments and blank lines",
        "Add harmless comments and blank lines to captured Prometheus text. The emitted metrics should stay the same.",
    ),
    "openmetrics-final-newline": (
        "OpenMetrics final newline",
        "Add or remove a final newline in captured Prometheus text. The emitted metrics should stay the same.",
    ),
    "openmetrics-help-text": (
        "OpenMetrics HELP text",
        "Change only HELP documentation text in captured Prometheus output. Metric output should not change.",
    ),
    "openmetrics-help-removal": (
        "OpenMetrics HELP removal",
        "Remove HELP documentation lines from captured Prometheus output. Metric output should not change.",
    ),
    "json-object-key-order": (
        "JSON object key order",
        "Reorder JSON object keys in captured responses. JSON key order should not change emitted output.",
    ),
    "json-whitespace": (
        "JSON whitespace",
        "Change insignificant JSON whitespace in captured responses. Emitted output should not change.",
    ),
    "json-string-escapes": (
        "JSON string escapes",
        "Change equivalent JSON string escaping in captured responses. Emitted output should not change.",
    ),
    "metadata-emitted-metrics": (
        "metadata.csv contract",
        "Every emitted metric should have a matching metadata.csv row with a compatible metric type.",
    ),
    "repeated-run-tag-stability": (
        "Repeated-run tag stability",
        "Run multiple readings with the same check instance. Tags should not duplicate or grow between readings.",
    ),
    "openmetrics-coverage": (
        "OpenMetrics coverage",
        "Report how much observed OpenMetrics input appears to be represented in emitted Datadog metrics and metadata.",
    ),
    "asset-query-metrics-in-metadata": (
        "Asset query metrics in metadata",
        "Dashboard and monitor queries for this integration should reference metrics documented in metadata.csv.",
    ),
    "asset-query-tags-seen-in-replay": (
        "Asset query tags seen in replay",
        "Report dashboard or monitor tag keys that were not seen in this replay fixture. This is usually a coverage signal, not automatically a product bug.",
    ),
    "output-finite-values": (
        "Finite metric values",
        "Every emitted metric value should be a real finite number, not NaN or infinity.",
    ),
    "rate-finite-values": (
        "Finite rate values",
        "Every emitted RATE value should be a real finite number, not NaN or infinity.",
    ),
    "monotonic-count-nonnegative": (
        "Non-negative monotonic counts",
        "Every emitted MONOTONIC_COUNT value should be non-negative, except explicitly ignored sum-style metrics.",
    ),
    # Backward-compatible grouping name used by older reports.
    "openmetrics-cache-mutation": (
        "OpenMetrics mutation",
        "Mutate cached OpenMetrics payloads and verify output stays stable when semantics are unchanged.",
    ),
}

CATEGORY_NEXT_STEPS = {
    "passed": "No action needed for this target.",
    "failed-before-replay-pbt": "Start with the setup or cache-seeding logs. The property tests did not get a clean chance to run.",
    "skipped-missing-cache": "Seed or restore a replay cache for this target, then rerun Replay PBT.",
    "replay-nondeterminism": "Check for time, ordering, random IDs, process state, or other values that the normalizer does not control yet.",
    "openmetrics-mutation": "Compare the original and mutated normalized outputs. If the mutation is valid, this may be a parser or integration bug.",
    "asset-metadata-mismatch": "Inspect the listed dashboard/monitor metric or tag. Usually this means metadata.csv or the asset query needs cleanup.",
    "metadata-contract": "Check metadata.csv against the emitted metric name/type. Add or fix metadata rows when the emitted metric is valid.",
    "coverage": "Use this as a coverage signal first. Check whether the fixture is sparse before treating it as a product bug.",
    "unsupported-negative": "Confirm whether this target is intentionally unsupported for replay or uses an error-path fixture. If yes, mark it out of scope.",
    "replay-harness": "This likely needs replay harness work: adapter coverage, cache matching, fixture selection, or environment mirroring.",
    "other-failed": "Open the failed test names and short errors below, then classify the failure before treating it as an integration bug.",
    "unknown": "The job did not report enough information. Check the workflow logs first.",
}


def property_label(name: Any) -> str:
    text = str(name or "")
    return PROPERTY_DEFINITIONS.get(text, (text.replace("-", " ").title(), ""))[0]


def property_description(name: Any) -> str:
    return PROPERTY_DEFINITIONS.get(str(name or ""), ("", ""))[1]


def property_display_md(name: Any) -> str:
    raw_name = str(name or "")
    label = property_label(raw_name)
    if not raw_name:
        return ""
    if label == raw_name:
        return f"`{md_escape(raw_name)}`"
    return f"**{md_escape(label)}**<br/><sub>`{md_escape(raw_name)}`</sub>"


def property_display_html(name: Any) -> str:
    raw_name = str(name or "")
    label = property_label(raw_name)
    if not raw_name:
        return ""
    if label == raw_name:
        return f"<code>{html.escape(raw_name)}</code>"
    return f"<strong>{html.escape(label)}</strong><br><small><code>{html.escape(raw_name)}</code></small>"


def sanitize_text(value: Any, *, max_len: int = MAX_TEXT) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    text = AUTH_TEXT_RE.sub(lambda m: f"{m.group('key')}={REDACTED}", text)
    text = KEY_VALUE_TEXT_RE.sub(lambda m: f"{m.group('key')}={REDACTED}", text)
    text = PRIVATE_KEY_TEXT_RE.sub(REDACTED, text)
    text = URL_CREDENTIAL_TEXT_RE.sub(r"\1" + REDACTED + "@", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def target_slug(row: dict[str, Any]) -> str:
    integration = row.get("integration") or "unknown"
    environment = row.get("environment") or "unknown"
    return f"{integration}:{environment}"


def short_test_name(test: str) -> str:
    test = test.split(" - ", 1)[0]
    return test.rsplit("::", 1)[-1]

TEST_DEFINITIONS = {
    "test_emitted_metrics_match_metadata": (
        "Emitted metrics match metadata.csv",
        "The check emitted a metric that is missing from metadata.csv or has a different type than metadata.csv declares.",
    ),
    "test_asset_query_metrics_match_metadata": (
        "Asset query metrics exist in metadata.csv",
        "A dashboard or monitor query references a metric that is not documented in metadata.csv.",
    ),
    "test_openmetrics_replay_coverage": (
        "OpenMetrics replay coverage",
        "The replay fixture did not cover enough of the observed OpenMetrics surface or metadata surface.",
    ),
    "test_cached_replay_is_deterministic_for_same_ref": (
        "Replay is deterministic",
        "Running the same check code against the same replay cache should produce the same normalized output.",
    ),
    "test_mutated_cache_matches_original_output": (
        "OpenMetrics mutations preserve output",
        "A semantically equivalent mutation of cached OpenMetrics input changed the check output.",
    ),
}


def test_label(name: Any) -> str:
    text = str(name or "")
    return TEST_DEFINITIONS.get(text, (text.replace("test_", "").replace("_", " ").capitalize(), ""))[0]


def test_description(name: Any) -> str:
    return TEST_DEFINITIONS.get(str(name or ""), ("", ""))[1]


def test_display_md(name: Any) -> str:
    raw_name = str(name or "")
    label = test_label(raw_name)
    if not raw_name:
        return ""
    if label == raw_name:
        return f"`{md_escape(raw_name)}`"
    return f"**{md_escape(label)}**<br/><sub>`{md_escape(raw_name)}`</sub>"


def classify(row: dict[str, Any]) -> str:
    status = row.get("status")
    if status == "passed":
        return "passed"
    if status == "failed-before-replay-pbt":
        return "failed-before-replay-pbt"
    if status == "skipped-missing-cache":
        return "skipped-missing-cache"

    haystack = "\n".join(
        [
            *(str(item) for item in row.get("failed_tests") or []),
            *(str(item) for item in row.get("short_errors") or []),
        ]
    ).lower()
    if not haystack:
        return "unknown" if not status else "other-failed"
    if "test_cached_replay_is_deterministic_for_same_ref" in haystack:
        return "replay-nondeterminism"
    if "mutated_cache_matches_original_output" in haystack:
        return "openmetrics-mutation"
    if "asset-query" in haystack or "asset query" in haystack:
        return "asset-metadata-mismatch"
    if (
        "test_emitted_metrics_match_metadata" in haystack
        or "test_asset_query_metrics_match_metadata" in haystack
        or "metadata.csv" in haystack
        or ("metadata" in haystack and ("missing" in haystack or "unemitted" in haystack))
    ):
        return "metadata-contract"
    if "openmetrics-coverage" in haystack or "coverage" in haystack:
        return "coverage"
    if "negative" in haystack or "unsupported" in haystack or "does not support" in haystack:
        return "unsupported-negative"
    if "adapter" in haystack or "replay" in haystack or "cache" in haystack or "fixture" in haystack:
        return "replay-harness"
    return "other-failed"


def summarize_failure(row: dict[str, Any]) -> str:
    failed_tests = row.get("failed_tests") or []
    short_errors = row.get("short_errors") or []
    if failed_tests:
        names = [test_label(short_test_name(str(item))) for item in failed_tests[:3]]
        more = len(failed_tests) - len(names)
        suffix = f" (+{more} more)" if more > 0 else ""
        return sanitize_text(", ".join(names) + suffix)
    if short_errors:
        return sanitize_text(short_errors[0])
    status = row.get("status") or "unknown"
    return sanitize_text(status)


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    category = classify(row)
    failed_tests = [short_test_name(str(item)) for item in (row.get("failed_tests") or [])]
    short_errors = [sanitize_text(item, max_len=MAX_TEXT) for item in (row.get("short_errors") or [])[:3]]
    return {
        "status": row.get("status", "unknown"),
        "category": category,
        "category_label": CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])[1],
        "integration": row.get("integration", ""),
        "environment": row.get("environment", ""),
        "target": target_slug(row),
        "fixture_ref": row.get("fixture_ref", ""),
        "target_ref": row.get("target_ref", ""),
        "mode": row.get("mode", ""),
        "readings": row.get("readings", ""),
        "shard_index": row.get("shard_index", ""),
        "shard_count": row.get("shard_count", ""),
        "failing_property_count": len(failed_tests),
        "failing_properties": failed_tests[:20],
        "short_errors": short_errors,
        "summary": summarize_failure(row),
    }


def find_target(path: Path) -> dict[str, Any]:
    for parent in [path, *path.parents]:
        target_path = parent / "target.json"
        if target_path.is_file():
            data = load_json(target_path)
            if isinstance(data, dict):
                return data
    return {}


def load_results(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.glob("**/result.json")):
        data = load_json(path)
        if isinstance(data, dict):
            rows.append(compact_row(data))
    rows.sort(key=lambda r: (r["status"], r["category"], r["integration"], r["environment"]))
    return rows


def load_findings_and_coverages(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    property_results: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    coverages: list[dict[str, Any]] = []

    for manifest_path in sorted(root.glob("**/property-result.json")):
        manifest = load_json(manifest_path)
        if not isinstance(manifest, dict):
            continue
        target = find_target(manifest_path.parent)
        property_name = manifest.get("property") or manifest_path.parent.name
        counts = manifest.get("counts") if isinstance(manifest.get("counts"), dict) else {}
        property_status = manifest.get("status", "")
        if counts.get("errors"):
            property_status = "failed"
        elif counts.get("warnings") and property_status == "passed":
            property_status = "warning"
        property_results.append(
            {
                "target": target_slug(target),
                "integration": target.get("integration", ""),
                "environment": target.get("environment", ""),
                "property": property_name,
                "status": property_status,
            }
        )
        for artifact in manifest.get("artifacts", []):
            if not isinstance(artifact, dict):
                continue
            rel_path = artifact.get("path")
            kind = artifact.get("kind")
            if not isinstance(rel_path, str) or rel_path.startswith("/") or ".." in Path(rel_path).parts:
                continue
            artifact_path = manifest_path.parent / rel_path
            if not artifact_path.is_file():
                continue
            data = load_json(artifact_path) if artifact.get("format") == "json" else None
            if kind == "findings" and isinstance(data, list):
                for finding in data:
                    if not isinstance(finding, dict):
                        continue
                    findings.append(
                        {
                            "level": sanitize_text(finding.get("level", ""), max_len=50),
                            "property": sanitize_text(property_name, max_len=100),
                            "check": sanitize_text(finding.get("check", ""), max_len=100),
                            "integration": target.get("integration", ""),
                            "environment": target.get("environment", ""),
                            "target": target_slug(target),
                            "metric": sanitize_text(finding.get("metric", ""), max_len=160),
                            "tag_key": sanitize_text(finding.get("tag_key", ""), max_len=120),
                            "path": sanitize_text(finding.get("path", ""), max_len=220),
                            "message": sanitize_text(finding.get("message", ""), max_len=400),
                            "query": sanitize_text(finding.get("query", ""), max_len=300),
                        }
                    )
            elif kind == "coverage" and isinstance(data, dict):
                endpoint = data.get("endpoint_to_emitted") or data.get("observed_to_emitted") or {}
                metadata = data.get("metadata_to_emitted") or data.get("supported_to_emitted") or {}
                coverages.append(
                    {
                        "property": property_name,
                        "integration": target.get("integration", ""),
                        "environment": target.get("environment", ""),
                        "target": target_slug(target),
                        "endpoint_count": endpoint.get("endpoint_count", endpoint.get("observed_count")),
                        "endpoint_emitted_count": endpoint.get("covered_count"),
                        "endpoint_missing_count": endpoint.get("missing_count"),
                        "endpoint_to_emitted_coverage": endpoint.get("coverage"),
                        "metadata_count": metadata.get("metadata_count", metadata.get("supported_count")),
                        "metadata_emitted_count": metadata.get("emitted_count"),
                        "metadata_unemitted_count": metadata.get("unemitted_count"),
                        "metadata_to_emitted_coverage": metadata.get("coverage"),
                    }
                )

    return property_results, findings, coverages


def coverage_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return max(0.0, min(1.0, number))


def pct(value: Any) -> str:
    number = coverage_number(value)
    if number is None:
        return ""
    return f"{number * 100:.1f}%"


def coverage_bar_md(value: Any, width: int = 18) -> str:
    number = coverage_number(value)
    if number is None:
        return ""
    filled = int(round(width * number))
    return f"`{'█' * filled}{'░' * (width - filled)}` {number * 100:.1f}%"


def coverage_bar_html(value: Any) -> str:
    number = coverage_number(value)
    if number is None:
        return ""
    percent = number * 100
    color = "var(--ok)" if percent >= 80 else "var(--warn)" if percent >= 40 else "var(--fail)"
    return (
        "<div class='coverage-bar' "
        f"aria-label='{percent:.1f}% coverage'>"
        f"<i style='width:{percent:.1f}%;background:{color}'></i>"
        f"<span>{percent:.1f}%</span></div>"
    )


def current_run_url() -> str:
    import os

    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "DataDog/integrations-core")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    return f"{server}/{repo}/actions/runs/{run_id}" if run_id else ""


def current_run_id() -> str:
    import os

    return os.environ.get("GITHUB_RUN_ID", "")


def attach_current_run(rows: list[dict[str, Any]]) -> None:
    run_id = current_run_id()
    run_url = current_run_url()
    if not run_id and not run_url:
        return
    for row in rows:
        row.setdefault("run_id", run_id)
        row.setdefault("run_url", run_url)


def finding_subject(finding: dict[str, Any]) -> str:
    return str(finding.get("metric") or finding.get("tag_key") or finding.get("query") or "")


def target_url(row: dict[str, Any]) -> str:
    return str(row.get("job_url") or row.get("run_url") or "")


def target_link_md(row: dict[str, Any]) -> str:
    target = md_escape(row.get("target", ""))
    url = target_url(row)
    if url:
        return f"[`{target}`]({md_escape(url)})"
    return f"`{target}`"


def target_link_html(row: dict[str, Any]) -> str:
    target = html.escape(str(row.get("target", "")))
    url = target_url(row)
    if url:
        label = "job" if row.get("job_url") else "run"
        return f"<a href='{html.escape(url)}'><code>{target}</code></a> <span class='tiny'>{label}</span>"
    return f"<code>{target}</code>"


def group_actionable_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actionable = [f for f in findings if (f.get("level") or "").lower() in {"error", "warning", "warn"}]
    groups: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for finding in actionable:
        key = (
            str(finding.get("target", "")),
            str(finding.get("property", "")),
            str(finding.get("check", "")),
            str(finding.get("path", "")),
            str(finding.get("message", "")),
        )
        group = groups.setdefault(
            key,
            {
                "target": finding.get("target", ""),
                "property": finding.get("property", ""),
                "property_label": property_label(finding.get("property", "")),
                "property_description": property_description(finding.get("property", "")),
                "check": finding.get("check", ""),
                "path": finding.get("path", ""),
                "message": finding.get("message", ""),
                "run_url": finding.get("run_url", ""),
                "job_url": finding.get("job_url", ""),
                "count": 0,
                "subjects": [],
            },
        )
        group["count"] += 1
        subject = finding_subject(finding)
        if subject and subject not in group["subjects"] and len(group["subjects"]) < 8:
            group["subjects"].append(subject)
    return sorted(groups.values(), key=lambda g: (-int(g["count"]), str(g["target"]), str(g["property"])))


def bar(count: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "░" * width
    filled = int(round(width * count / total))
    return "█" * filled + "░" * (width - filled)


def md_escape(text: Any) -> str:
    return sanitize_text(text, max_len=MAX_DETAIL_TEXT).replace("|", "\\|")


def property_results_for_target(property_results: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    return sorted(
        [row for row in property_results if row.get("target") == target],
        key=lambda row: (str(row.get("property", "")), str(row.get("status", ""))),
    )


def findings_for_target(findings: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    return [finding for finding in findings if finding.get("target") == target]


def coverages_for_target(coverages: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    return [coverage for coverage in coverages if coverage.get("target") == target]


def replay_reproduce_command(row: dict[str, Any]) -> str:
    integration = str(row.get("integration") or "<integration>")
    environment = str(row.get("environment") or "<environment>")
    fixture_ref = str(row.get("fixture_ref") or "<fixture-ref>")
    target_ref = str(row.get("target_ref") or "<target-ref>")
    readings = str(row.get("readings") or "2")
    return " \\\n  ".join(
        [
            f"ddev env replay-pbt {integration} {environment}",
            f"--fixture-ref {fixture_ref}",
            f"--target-ref {target_ref}",
            "--replay-cache latest",
            f"--readings {readings}",
            "--adapters requests,subprocess,process,psycopg,clickhouse-connect",
            "--artifacts /tmp/replay-pbt-repro",
            "--overwrite",
        ]
    )


def build_individual_target_markdown(
    row: dict[str, Any],
    property_results: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    coverages: list[dict[str, Any]],
) -> list[str]:
    category = row.get("category", "unknown")
    icon, label, description = CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])
    target = row.get("target", "")
    target_properties = property_results_for_target(property_results, str(target))
    target_findings = findings_for_target(findings, str(target))
    target_coverages = coverages_for_target(coverages, str(target))

    lines = [
        "## Individual target report",
        "",
        "This section is meant to be readable on its own. It explains what was tested for this integration, what failed or passed, and what to try next.",
        "",
        "### Target",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Integration | `{md_escape(row.get('integration', ''))}` |",
        f"| Environment | `{md_escape(row.get('environment', ''))}` |",
        f"| Fixture ref | `{md_escape(row.get('fixture_ref', ''))}` |",
        f"| Target ref | `{md_escape(row.get('target_ref', ''))}` |",
        f"| Readings | `{md_escape(row.get('readings', ''))}` |",
        f"| Replay cache key | `{md_escape(row.get('cache_key', ''))}` |",
        f"| Status | {status_icon(row.get('status'))} **{md_escape(status_label(row.get('status')))}** |",
        f"| Category | {icon} **{md_escape(label)}** |",
        "",
        "### What this means",
        "",
        f"{description}",
        "",
        f"**Short summary:** {md_escape(row.get('summary', ''))}",
        "",
        f"**Suggested next step:** {md_escape(CATEGORY_NEXT_STEPS.get(str(category), CATEGORY_NEXT_STEPS['unknown']))}",
        "",
    ]

    lines.extend(["### Property results", ""])
    if target_properties:
        lines.extend(["| Property | Status | What it checks |", "|---|---|---|"])
        for prop in target_properties:
            prop_name = prop.get("property", "")
            lines.append(
                f"| {property_display_md(prop_name)} | {status_icon(prop.get('status'))} {md_escape(status_label(prop.get('status')))} | {md_escape(property_description(prop_name))} |"
            )
    elif row.get("status") in {"failed-before-replay-pbt", "skipped-missing-cache"}:
        lines.append("Property tests did not run for this target. The job stopped before replay-PBT could produce per-property results.")
    else:
        lines.append("No per-property manifests were collected for this target. Check the workflow log if this was unexpected.")
    lines.append("")

    failed_tests = row.get("failing_properties") or []
    short_errors = row.get("short_errors") or []
    if failed_tests or short_errors:
        lines.extend(["### Failure details from pytest", ""])
        if failed_tests:
            lines.append("Failed checks:")
            for item in failed_tests[:12]:
                description = test_description(item)
                suffix = f" — {md_escape(description)}" if description else ""
                lines.append(f"- {test_display_md(item)}{suffix}")
            lines.append("")
        if short_errors:
            lines.append("Short error excerpts:")
            for item in short_errors[:6]:
                lines.append(f"- {md_escape(item)}")
            lines.append("")

    lines.extend(["### Collected findings", ""])
    if target_findings:
        lines.extend(["| Level | Property | Subject | Message |", "|---|---|---|---|"])
        for finding in target_findings[:12]:
            subject = finding_subject(finding)
            lines.append(
                f"| `{md_escape(finding.get('level', ''))}` | `{md_escape(finding.get('property', ''))}` | `{md_escape(subject)}` | {md_escape(finding.get('message', ''))} |"
            )
        if len(target_findings) > 12:
            lines.append(f"| _… {len(target_findings) - 12} more_ | | | See `findings.tsv`. |")
    else:
        lines.append("No allowlisted property findings were collected for this target.")
    lines.append("")

    if target_coverages:
        lines.extend(["### Coverage reported for this target", ""])
        lines.extend(["| Property | Endpoint → emitted | metadata.csv → emitted | Endpoint count | Metadata count |", "|---|---|---|---:|---:|"])
        for coverage in target_coverages:
            lines.append(
                f"| {property_display_md(coverage.get('property', ''))} | {coverage_bar_md(coverage.get('endpoint_to_emitted_coverage'))} | {coverage_bar_md(coverage.get('metadata_to_emitted_coverage'))} | {coverage.get('endpoint_count') or ''} | {coverage.get('metadata_count') or ''} |"
            )
        lines.append("")

    lines.extend(
        [
            "### Reproduce locally",
            "",
            "This uses the latest replay cache for this integration/environment. If the cache is missing locally, seed or restore it first.",
            "",
            "```bash",
            replay_reproduce_command(row),
            "```",
            "",
        ]
    )
    return lines


def replay_step_counts(rows: list[dict[str, Any]], findings: list[dict[str, Any]], coverages: list[dict[str, Any]]) -> dict[str, int]:
    status_counts = Counter(row["status"] for row in rows)
    artifact_targets = {finding.get("target") for finding in findings if finding.get("target")}
    artifact_targets.update(coverage.get("target") for coverage in coverages if coverage.get("target"))
    return {
        "targets": len(rows),
        "cache_ready": status_counts.get("passed", 0) + status_counts.get("failed", 0),
        "cache_blocked": status_counts.get("failed-before-replay-pbt", 0) + status_counts.get("skipped-missing-cache", 0),
        "replay_passed": status_counts.get("passed", 0),
        "replay_failed": status_counts.get("failed", 0),
        "replay_not_run": status_counts.get("failed-before-replay-pbt", 0) + status_counts.get("skipped-missing-cache", 0),
        "artifact_targets": len(artifact_targets),
        "findings": len(findings),
        "coverage_reports": len(coverages),
    }


def target_step_state(row: dict[str, Any], artifact_targets: set[str]) -> list[tuple[str, str]]:
    status = row.get("status")
    target = row.get("target", "")
    cache_state = "ok" if status in {"passed", "failed"} else "blocked" if status == "failed-before-replay-pbt" else "skipped"
    replay_state = "ok" if status == "passed" else "fail" if status == "failed" else "blocked"
    artifact_state = "ok" if target in artifact_targets else "none"
    return [
        ("Matrix", "ok"),
        ("Cache", cache_state),
        ("Replay", replay_state),
        ("Artifacts", artifact_state),
    ]


def build_replay_flow_markdown(rows: list[dict[str, Any]], findings: list[dict[str, Any]], coverages: list[dict[str, Any]]) -> list[str]:
    counts = replay_step_counts(rows, findings, coverages)
    return [
        "## What this job is doing",
        "",
        "Replay PBT is a coverage and regression experiment for Agent integrations. Instead of starting every vendor service for every property check, it records a small fixture once, replays that fixture against the check code, and asks targeted questions about the output.",
        "",
        "```mermaid",
        "flowchart LR",
        f"  A[\"Pick targets<br/>{counts['targets']} in this shard\"] --> B[\"Restore replay cache\"]",
        "  B -->|cache hit| C[\"Run replay PBT\"]",
        "  B -->|cache miss and seeding enabled| S[\"Seed with compare-check<br/>start E2E env, record fixture\"] --> C",
        "  B -->|cache miss and seeding disabled| K[\"Skip target\"]",
        f"  C --> D[\"Property checks<br/>{counts['replay_passed']} passed / {counts['replay_failed']} failed\"]",
        f"  D --> E[\"Findings<br/>{counts['findings']} findings, {counts['coverage_reports']} coverage reports\"]",
        "  E --> R[\"Report\"]",
        "```",
        "",
        "### Conceptual model",
        "",
        "| Piece | Description |",
        "|---|---|",
        "| Replay cache | Sanitized input/output fixture for one integration environment and fixture ref. It is stored in GitHub Actions cache, not uploaded as a report artifact. |",
        "| Seeding | If a cache is missing and `seed_missing_caches=true`, the job starts the E2E environment and runs compare-check once to create a replay cache. |",
        "| Replay PBT | Runs the check against cached inputs, mutates safe replay inputs, and verifies properties such as determinism, metadata consistency, and OpenMetrics coverage. |",
        "| Findings | Small, allowlisted JSON records explaining what property failed. Raw replay caches, configs, captures, and logs are excluded from report artifacts. |",
        "",
        "### This shard at a glance",
        "",
        "| Step | Result in this shard |",
        "|---|---:|",
        f"| Targets selected | {counts['targets']} |",
        f"| Cache ready | {counts['cache_ready']} |",
        f"| Cache blocked/skipped | {counts['cache_blocked']} |",
        f"| Replay passed | {counts['replay_passed']} |",
        f"| Replay failed | {counts['replay_failed']} |",
        f"| Replay not run | {counts['replay_not_run']} |",
        f"| Finding groups | {len(group_actionable_findings(findings))} |",
        "",
    ]

def build_markdown(
    rows: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    coverages: list[dict[str, Any]],
    *,
    mode: str,
    shard: str,
    target_count: str,
    shard_runs: list[dict[str, Any]] | None = None,
    artifact_name: str = "replay-pbt-report",
    property_results: list[dict[str, Any]] | None = None,
) -> str:
    status_counts = Counter(row["status"] for row in rows)
    category_counts = Counter(row["category"] for row in rows if row["category"] != "passed")
    total = len(rows)
    passed = status_counts.get("passed", 0)
    failed = total - passed
    current_url = current_run_url()
    current_id = current_run_id()
    groups = group_actionable_findings(findings)
    property_results = property_results or []

    lines: list[str] = []
    lines.extend(
        [
            "# Replay PBT report",
            "",
            f"**Result:** {'✅ Passed' if failed == 0 and total else '❌ Needs attention'}  ",
            f"**Mode:** `{mode}`  ",
            f"**Shard:** `{shard}`  ",
            f"**Targets in this shard:** `{target_count}`  ",
            f"**Result files collected:** `{total}`  ",
            f"**Rich dashboard:** download the `{artifact_name}` artifact and open `report.html`.",
            "",
        ]
    )
    if current_url and not shard_runs:
        lines.extend([f"**This shard run:** [{current_id or 'current run'}]({current_url})", ""])
    if shard_runs:
        lines.extend(["## Shard runs", "", "| Shard | Conclusion | Link |", "|---|---|---|"])
        for run in shard_runs:
            run_id = md_escape(run.get("run_id", ""))
            title = md_escape(run.get("display_title", ""))
            conclusion = md_escape(run.get("conclusion", ""))
            url = md_escape(run.get("url", ""))
            lines.append(f"| `{run_id}` {title} | `{conclusion}` | [Open run]({url}) |")
        lines.append("")

    lines.extend(build_replay_flow_markdown(rows, findings, coverages))
    if len(rows) == 1:
        lines.extend(build_individual_target_markdown(rows[0], property_results, findings, coverages))
    lines.extend(
        [
            "## Outcome summary",
            "",
            "| Status | Count | Distribution |",
            "|---|---:|---|",
        ]
    )
    for status, count in sorted(status_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {status_icon(status)} **{md_escape(status_label(status))}**<br/><sub>`{md_escape(status)}`</sub> | {count} | `{bar(count, total)}` |")
    lines.append("")

    lines.extend(["## Failure categories", ""])
    if category_counts:
        lines.extend(["| Category | Count | What it means | Example targets |", "|---|---:|---|---|"])
        examples_by_category: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            if row["category"] != "passed" and len(examples_by_category[row["category"]]) < 4:
                examples_by_category[row["category"]].append(target_link_md(row))
        for category, count in category_counts.most_common():
            icon, label, description = CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])
            examples = ", ".join(examples_by_category[category])
            lines.append(f"| {icon} {label} | {count} | {description} | {examples} |")
    else:
        lines.append("No failures reported.")
    lines.append("")

    lines.extend(["## Actionable finding groups", ""])
    if groups:
        lines.append("Findings are grouped for humans. Repeated metric/tag rows are collapsed into one line with examples.")
        lines.append("")
        lines.extend(["| Target | Finding type | Count | Examples | Message |", "|---|---|---:|---|---|"])
        for group in groups[:12]:
            examples = ", ".join(f"`{md_escape(item)}`" for item in group["subjects"][:5])
            if group["count"] > len(group["subjects"][:5]):
                examples += f", +{group['count'] - len(group['subjects'][:5])} more"
            lines.append(
                f"| {target_link_md(group)} | **{md_escape(group['property_label'])}**<br/><sub>`{md_escape(group['property'])}`</sub> | {group['count']} | {examples} | {md_escape(group['message'])} |"
            )
        if len(groups) > 12:
            lines.append(f"\n_… {len(groups) - 12} more grouped finding rows in `report.html` and `findings.tsv`._")
    else:
        lines.append("No actionable property findings collected.")
    lines.append("")

    lines.extend(["## OpenMetrics coverage", ""])
    if coverages:
        lines.extend(["| Target | Endpoint → emitted | metadata.csv → emitted | Endpoint count | Metadata count |", "|---|---|---|---:|---:|"])
        sorted_coverages = sorted(
            coverages,
            key=lambda c: (
                -1 if c.get("endpoint_to_emitted_coverage") is None else float(c.get("endpoint_to_emitted_coverage") or 0),
                c.get("target", ""),
            ),
            reverse=True,
        )
        for coverage in sorted_coverages[:20]:
            lines.append(
                f"| {target_link_md(coverage)} | {coverage_bar_md(coverage.get('endpoint_to_emitted_coverage'))} | {coverage_bar_md(coverage.get('metadata_to_emitted_coverage'))} | {coverage.get('endpoint_count') or ''} | {coverage.get('metadata_count') or ''} |"
            )
        if len(sorted_coverages) > 20:
            remaining = sorted_coverages[20:]
            lines.append("")
            lines.append(f"<details><summary>📈 More OpenMetrics coverage rows ({len(remaining)})</summary>")
            lines.append("")
            lines.extend(["| Target | Endpoint → emitted | metadata.csv → emitted | Endpoint count | Metadata count |", "|---|---|---|---:|---:|"])
            for coverage in remaining:
                lines.append(
                    f"| {target_link_md(coverage)} | {coverage_bar_md(coverage.get('endpoint_to_emitted_coverage'))} | {coverage_bar_md(coverage.get('metadata_to_emitted_coverage'))} | {coverage.get('endpoint_count') or ''} | {coverage.get('metadata_count') or ''} |"
                )
            lines.append("")
            lines.append("</details>")
    else:
        lines.append("No OpenMetrics coverage reports collected.")
    lines.append("")

    lines.extend(["## Failed target details", ""])
    failed_rows = [row for row in rows if row["status"] != "passed"]
    if failed_rows:
        for category, grouped_rows in sorted(
            ((category, [row for row in failed_rows if row["category"] == category]) for category in category_counts),
            key=lambda item: (-len(item[1]), item[0]),
        ):
            icon, label, _ = CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])
            lines.append(f"<details><summary>{icon} {label} ({len(grouped_rows)})</summary>")
            lines.append("")
            lines.append("| Target | Fixture | Failing properties | Summary | Shard |")
            lines.append("|---|---|---:|---|---|")
            for row in grouped_rows[:50]:
                shard_link = f"[run]({row.get('run_url')})" if row.get("run_url") else ""
                lines.append(
                    f"| {target_link_md(row)} | `{md_escape(row.get('fixture_ref', ''))}` | {row.get('failing_property_count', 0)} | {md_escape(row.get('summary', ''))} | {shard_link} |"
                )
            if len(grouped_rows) > 50:
                lines.append(f"| _… {len(grouped_rows) - 50} more_ | | | | |")
            lines.append("")
            lines.append("</details>")
            lines.append("")
    else:
        lines.append("No failed targets.")
    return "\n".join(lines) + "\n"

def build_html(
    markdown: str,
    rows: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    coverages: list[dict[str, Any]],
    shard_runs: list[dict[str, Any]] | None = None,
    property_results: list[dict[str, Any]] | None = None,
) -> str:
    status_counts = Counter(row["status"] for row in rows)
    category_counts = Counter(row["category"] for row in rows if row["category"] != "passed")
    counts = replay_step_counts(rows, findings, coverages)
    groups = group_actionable_findings(findings)
    property_results = property_results or []
    artifact_targets = {finding.get("target") for finding in findings if finding.get("target")}
    artifact_targets.update(coverage.get("target") for coverage in coverages if coverage.get("target"))
    total = len(rows) or 1
    passed = status_counts.get("passed", 0)
    failed = total - passed

    def esc(value: Any) -> str:
        return html.escape(str(value or ""))

    status_cards = "".join(
        f"<div class='stat'><span>{esc(status_label(status))}</span><strong>{count}</strong><div class='bar'><i style='width:{100*count/total:.1f}%'></i></div><small><code>{esc(status)}</code></small></div>"
        for status, count in status_counts.most_common()
    )
    steps = [
        ("1", "Select shard targets", f"{counts['targets']} target result(s)", "The dispatcher splits all declared integration/env pairs into shards so each workflow run stays small."),
        ("2", "Restore replay cache", f"{counts['cache_ready']} ready · {counts['cache_blocked']} blocked", "The job restores `.ddev/replay/<integration>/<env>` from GitHub Actions cache. This cache is not uploaded as a report artifact."),
        ("3", "Seed if allowed", "cache miss → compare-check", "When `seed_missing_caches=true`, the job starts the E2E env once and records a sanitized fixture for future replay."),
        ("4", "Run Replay PBT", f"{counts['replay_passed']} passed · {counts['replay_failed']} failed", "The check runs without a live Agent against cached input, then properties mutate or inspect replay output."),
        ("5", "Collect findings", f"{len(groups)} grouped findings", "Only lightweight allowlisted findings/results/coverage are uploaded. Raw captures, configs, logs, and replay caches are excluded."),
        ("6", "Read this report", "HTML dashboard + machine files", "The dashboard groups repeated findings for humans; JSON/TSV files remain available for deeper analysis."),
    ]
    step_cards = "".join(
        f"<article class='step'><b>{num}</b><h3>{esc(title)}</h3><p class='step-metric'>{esc(metric)}</p><p>{esc(desc)}</p></article>"
        for num, title, metric, desc in steps
    )
    seed_diagram = """
    <svg viewBox='0 0 980 250' role='img' aria-label='Replay PBT cache seeding flow'>
      <defs><marker id='arrow' markerWidth='10' markerHeight='10' refX='8' refY='3' orient='auto'><path d='M0,0 L0,6 L9,3 z' fill='#57606a'/></marker></defs>
      <rect class='box' x='20' y='80' width='145' height='70' rx='14'/><text x='92' y='108' text-anchor='middle'>Shard target</text><text x='92' y='130' text-anchor='middle' class='small'>integration + env</text>
      <line class='arrow' x1='165' y1='115' x2='245' y2='115'/>
      <rect class='box' x='245' y='80' width='150' height='70' rx='14'/><text x='320' y='108' text-anchor='middle'>Restore cache</text><text x='320' y='130' text-anchor='middle' class='small'>GitHub Actions cache</text>
      <line class='arrow' x1='395' y1='115' x2='475' y2='80'/><text x='430' y='84' class='small'>hit</text>
      <rect class='box ok' x='475' y='35' width='145' height='70' rx='14'/><text x='548' y='63' text-anchor='middle'>Replay PBT</text><text x='548' y='85' text-anchor='middle' class='small'>property checks</text>
      <line class='arrow' x1='395' y1='130' x2='475' y2='170'/><text x='420' y='166' class='small'>miss + seed</text>
      <rect class='box warn' x='475' y='145' width='145' height='70' rx='14'/><text x='548' y='173' text-anchor='middle'>Seed cache</text><text x='548' y='195' text-anchor='middle' class='small'>start E2E + compare-check</text>
      <line class='arrow' x1='620' y1='180' x2='690' y2='95'/>
      <line class='arrow' x1='620' y1='70' x2='690' y2='70'/>
      <rect class='box' x='690' y='35' width='130' height='70' rx='14'/><text x='755' y='63' text-anchor='middle'>Findings</text><text x='755' y='85' text-anchor='middle' class='small'>allowlisted JSON</text>
      <line class='arrow' x1='820' y1='70' x2='885' y2='70'/>
      <rect class='box' x='885' y='35' width='80' height='70' rx='14'/><text x='925' y='63' text-anchor='middle'>Report</text><text x='925' y='85' text-anchor='middle' class='small'>HTML</text>
      <line class='arrow' x1='395' y1='150' x2='690' y2='210'/><text x='475' y='232' class='small'>miss + no seeding → skipped target</text>
    </svg>
    """
    shard_rows = "".join(
        f"<tr><td><code>{esc(run.get('run_id'))}</code></td><td>{esc(run.get('display_title'))}</td><td>{esc(run.get('conclusion'))}</td><td><a href='{esc(run.get('url'))}'>Open shard</a></td></tr>"
        for run in (shard_runs or [])
    )
    current_link = current_run_url()
    current_run_html = (
        '<a href="{}">Open the GitHub Actions run</a>'.format(esc(current_link))
        if current_link
        else 'This report was generated for a single shard run.'
    )
    shard_section = (
        f"<section class='card'><h2>Shard runs</h2><p>Use these links to jump from the combined report to the original shard runs.</p><table><thead><tr><th>Run ID</th><th>Title</th><th>Conclusion</th><th>Link</th></tr></thead><tbody>{shard_rows}</tbody></table></section>"
        if shard_rows
        else f"<section class='card'><h2>This shard</h2><p>{current_run_html}</p></section>"
    )
    individual_section = ""
    if len(rows) == 1:
        row = rows[0]
        category = row.get("category", "unknown")
        icon, label, description = CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])
        target_name = str(row.get("target", ""))
        prop_rows = "".join(
            f"<tr><td>{property_display_html(prop.get('property'))}</td><td>{esc(status_icon(prop.get('status')))} {esc(status_label(prop.get('status')))}</td><td>{esc(property_description(prop.get('property')))}</td></tr>"
            for prop in property_results_for_target(property_results, target_name)
        ) or "<tr><td colspan='3'>No per-property manifests were collected for this target.</td></tr>"
        target_coverage_rows = "".join(
            f"<tr><td>{property_display_html(coverage.get('property'))}</td><td>{coverage_bar_html(coverage.get('endpoint_to_emitted_coverage'))}</td><td>{coverage_bar_html(coverage.get('metadata_to_emitted_coverage'))}</td><td>{esc(coverage.get('endpoint_count'))}</td><td>{esc(coverage.get('metadata_count'))}</td></tr>"
            for coverage in coverages_for_target(coverages, target_name)
        ) or "<tr><td colspan='5'>No coverage reports collected for this target.</td></tr>"
        command = esc(replay_reproduce_command(row))
        individual_section = f"""
<section class='card'>
  <h2>Individual target report</h2>
  <p>This section is meant to be readable on its own. It explains what was tested for this integration, what failed or passed, and what to try next.</p>
  <table><tbody>
    <tr><th>Integration</th><td><code>{esc(row.get('integration'))}</code></td></tr>
    <tr><th>Environment</th><td><code>{esc(row.get('environment'))}</code></td></tr>
    <tr><th>Fixture ref</th><td><code>{esc(row.get('fixture_ref'))}</code></td></tr>
    <tr><th>Target ref</th><td><code>{esc(row.get('target_ref'))}</code></td></tr>
    <tr><th>Status</th><td>{esc(status_icon(row.get('status')))} <strong>{esc(status_label(row.get('status')))}</strong><br><small><code>{esc(row.get('status'))}</code></small></td></tr>
    <tr><th>Category</th><td>{esc(icon)} <strong>{esc(label)}</strong></td></tr>
  </tbody></table>
  <h3>What this means</h3>
  <p>{esc(description)}</p>
  <p><strong>Short summary:</strong> {esc(row.get('summary'))}</p>
  <p><strong>Suggested next step:</strong> {esc(CATEGORY_NEXT_STEPS.get(str(category), CATEGORY_NEXT_STEPS['unknown']))}</p>
  <h3>Property results</h3>
  <table><thead><tr><th>Property</th><th>Status</th><th>What it checks</th></tr></thead><tbody>{prop_rows}</tbody></table>
  <h3>Coverage chart</h3>
  <p class='muted'>Coverage is a signal about how much this replay fixture exercises, not a pass/fail grade by itself.</p>
  <table><thead><tr><th>Property</th><th>Endpoint → emitted</th><th>metadata.csv → emitted</th><th>Endpoint count</th><th>Metadata count</th></tr></thead><tbody>{target_coverage_rows}</tbody></table>
  <h3>Reproduce locally</h3>
  <pre><code>{command}</code></pre>
</section>
"""
    category_rows = "".join(
        f"<tr><td>{esc(CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS['unknown'])[0])} {esc(CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS['unknown'])[1])}</td><td>{count}</td><td>{esc(CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS['unknown'])[2])}</td></tr>"
        for category, count in category_counts.most_common()
    )
    finding_cards = "".join(
        "<article class='finding'>"
        f"<div><strong>{esc(group['property_label'])}</strong> {target_link_html(group)}</div>"
        f"<p>{esc(group['message'])}</p>"
        f"<p class='muted'>{esc(group['property_description'])}</p>"
        f"<p><span class='badge'>{group['count']} repeated row(s)</span> <code>{esc(group['path'])}</code></p>"
        f"<p class='examples'>{', '.join(f'<code>{esc(item)}</code>' for item in group['subjects'][:8])}</p>"
        "</article>"
        for group in groups[:30]
    ) or "<p>No actionable finding groups collected.</p>"
    target_row_parts = []
    for row in rows:
        pipeline_html = ''.join(
            '<span class="pill {}">{}: {}</span>'.format(esc(state), esc(label), esc(state))
            for label, state in target_step_state(row, artifact_targets)
        )
        run_link = '<a href="{}">run</a>'.format(esc(row.get('run_url'))) if row.get('run_url') else ''
        target_row_parts.append(
            "<tr>"
            f"<td>{target_link_html(row)}</td>"
            f"<td>{pipeline_html}</td>"
            f"<td>{esc(status_icon(row['status']))} {esc(status_label(row['status']))}<br><small><code>{esc(row['status'])}</code></small></td>"
            f"<td>{esc(row['category_label'])}</td>"
            f"<td>{esc(row['summary'])}</td>"
            f"<td>{run_link}</td>"
            "</tr>"
        )
    target_rows = ''.join(target_row_parts)
    coverage_rows = "".join(
        f"<tr><td>{target_link_html(c)}</td><td>{coverage_bar_html(c.get('endpoint_to_emitted_coverage'))}</td><td>{coverage_bar_html(c.get('metadata_to_emitted_coverage'))}</td><td>{esc(c.get('endpoint_count'))}</td><td>{esc(c.get('metadata_count'))}</td></tr>"
        for c in sorted(coverages, key=lambda item: str(item.get('target', '')))[:80]
    ) or "<tr><td colspan='5'>No coverage reports collected.</td></tr>"
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Replay PBT dashboard</title>
<style>
:root{{--ok:#1f883d;--fail:#cf222e;--warn:#bf8700;--muted:#6e7781;--line:#d0d7de;--bg:#f6f8fa;--purple:#8250df;--blue:#0969da}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;line-height:1.45;color:#1f2328;background:#f6f8fa}}
main{{max-width:1280px;margin:0 auto;padding:2rem}} .hero{{background:linear-gradient(135deg,#1f2328,#563d7c);color:white;border-radius:22px;padding:2rem;margin-bottom:1rem;box-shadow:0 12px 35px rgba(31,35,40,.18)}}
.hero h1{{margin:.2rem 0;font-size:2.2rem}} .hero p{{max-width:820px;color:#eef2ff}} .hero .result{{display:inline-flex;gap:.5rem;align-items:center;background:{'#dafbe1' if failed == 0 and rows else '#ffebe9'};color:{'#116329' if failed == 0 and rows else '#82071e'};padding:.35rem .7rem;border-radius:999px;font-weight:700}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1rem}} .card{{background:white;border:1px solid var(--line);border-radius:16px;padding:1rem;margin:1rem 0;box-shadow:0 1px 2px rgba(31,35,40,.06)}}
.stat{{background:white;border:1px solid var(--line);border-radius:14px;padding:1rem}} .stat span{{display:block;color:var(--muted)}} .stat strong{{font-size:2rem}} .bar{{height:10px;background:#eaeef2;border-radius:999px;overflow:hidden}} .bar i{{display:block;height:100%;background:var(--purple)}}
.coverage-bar{{position:relative;min-width:150px;height:22px;background:#eaeef2;border-radius:999px;overflow:hidden}} .coverage-bar i{{display:block;height:100%;min-width:2px}} .coverage-bar span{{position:absolute;inset:0;display:grid;place-items:center;font-size:12px;font-weight:700;color:#1f2328;text-shadow:0 1px 0 rgba(255,255,255,.7)}}
.flow{{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:.75rem}} .step{{background:white;border:1px solid var(--line);border-radius:16px;padding:1rem;position:relative}} .step b{{display:grid;place-items:center;background:#eef2ff;color:var(--purple);width:2rem;height:2rem;border-radius:999px}} .step h3{{margin:.6rem 0 .2rem}} .step-metric{{font-weight:700;color:#24292f}}
.seed svg{{width:100%;height:auto}} .box{{fill:white;stroke:#8c959f;stroke-width:2}} .box.ok{{stroke:var(--ok)}} .box.warn{{stroke:var(--warn)}} .arrow{{stroke:#57606a;stroke-width:2;marker-end:url(#arrow)}} text{{font-size:15px;fill:#24292f}} text.small{{font-size:12px;fill:#57606a}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}td,th{{border:1px solid var(--line);padding:.5rem;text-align:left;vertical-align:top}}th{{background:var(--bg)}} code{{background:var(--bg);padding:.1rem .25rem;border-radius:4px}} a{{color:var(--blue)}}
.finding{{border:1px solid var(--line);border-left:5px solid var(--warn);border-radius:14px;padding:1rem;background:white;margin:.75rem 0}} .muted{{color:var(--muted)}} .badge{{background:#fff8c5;color:#633c01;border:1px solid #fae17d;border-radius:999px;padding:.1rem .45rem}} .examples code{{margin:.12rem;display:inline-block}}
.pill{{display:inline-block;border-radius:999px;padding:.12rem .45rem;margin:.1rem;font-size:12px;border:1px solid var(--line)}} .pill.ok{{background:#dafbe1;color:#116329;border-color:#aceebb}}.pill.fail{{background:#ffebe9;color:#82071e;border-color:#ffcecb}}.pill.warn,.pill.blocked{{background:#fff8c5;color:#633c01;border-color:#fae17d}}.pill.skipped,.pill.none{{background:#f6f8fa;color:#57606a}}
</style></head><body><main>
<section class='hero'><span class='result'>{'✅ Passed' if failed == 0 and rows else '❌ Needs attention'}</span><h1>Replay PBT dashboard</h1><p>A view of replay-based property testing for Agent integrations. It explains the cache/seeding flow, links shards, and groups repeated findings.</p></section>
<section class='grid'>{status_cards}<div class='stat'><span>Finding groups</span><strong>{len(groups)}</strong></div><div class='stat'><span>Coverage reports</span><strong>{len(coverages)}</strong></div></section>
<section class='card'><h2>How the concept works</h2><div class='flow'>{step_cards}</div></section>
<section class='card seed'><h2>Cache seeding flow</h2><p>Seeding is only used when the replay cache is missing and the workflow input permits it. The generated cache stays in GitHub Actions cache; the report uploads only lightweight findings/results.</p>{seed_diagram}</section>
{shard_section}
{individual_section}
<section class='card'><h2>Failure categories</h2><table><thead><tr><th>Category</th><th>Count</th><th>Meaning</th></tr></thead><tbody>{category_rows or '<tr><td colspan="3">No failures</td></tr>'}</tbody></table></section>
<section class='card'><h2>Actionable finding groups</h2><p>Repeated metric/tag rows are collapsed. Use the examples to see the shape of the issue, then open <code>findings.tsv</code> for raw rows if needed.</p>{finding_cards}</section>
<section class='card'><h2>Targets by workflow step</h2><table><thead><tr><th>Target</th><th>Pipeline state</th><th>Status</th><th>Category</th><th>Summary</th><th>Shard</th></tr></thead><tbody>{target_rows}</tbody></table></section>
<section class='card'><h2>OpenMetrics coverage</h2><table><thead><tr><th>Target</th><th>Endpoint → emitted</th><th>metadata.csv → emitted</th><th>Endpoint count</th><th>Metadata count</th></tr></thead><tbody>{coverage_rows}</tbody></table></section>
</main></body></html>"""

def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_zip(zip_path: Path, report_dir: Path) -> None:
    allowed = {
        "manifest.json",
        "report.md",
        "report.html",
        "summary.json",
        "summary.tsv",
        "targets.json",
        "targets.tsv",
        "failure-categories.json",
        "failure-categories.tsv",
        "property-results.json",
        "findings.json",
        "findings.tsv",
        "coverage-summary.json",
        "coverage-summary.tsv",
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(report_dir.iterdir()):
            if path.name in allowed and path.is_file():
                zf.write(path, path.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--mode", default="")
    parser.add_argument("--shard", default="")
    parser.add_argument("--target-count", default="")
    parser.add_argument("--artifact-name", default="replay-pbt-report")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_results(args.results)
    attach_current_run(rows)
    property_results, findings, coverages = load_findings_and_coverages(args.findings)
    attach_current_run(findings)
    attach_current_run(coverages)
    attach_current_run(property_results)

    status_counts = Counter(row["status"] for row in rows)
    category_counts = Counter(row["category"] for row in rows if row["category"] != "passed")
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "shard": args.shard,
        "target_count": args.target_count,
        "result_files_collected": len(rows),
        "status_counts": dict(status_counts),
        "failure_category_counts": dict(category_counts),
        "property_result_count": len(property_results),
        "finding_count": len(findings),
        "coverage_count": len(coverages),
    }
    categories = [
        {
            "category": category,
            "label": CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])[1],
            "count": count,
            "description": CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])[2],
        }
        for category, count in category_counts.most_common()
    ]

    markdown = build_markdown(
        rows,
        findings,
        coverages,
        mode=args.mode,
        shard=args.shard,
        target_count=args.target_count,
        artifact_name=args.artifact_name,
        property_results=property_results,
    )
    html_report = build_html(markdown, rows, findings, coverages, property_results=property_results)

    (args.out_dir / "report.md").write_text(markdown)
    (args.out_dir / "report.html").write_text(html_report)
    write_json(args.out_dir / "manifest.json", {"schema_version": 1, "allowlisted_files_only": True, "excluded_by_policy": ["raw captures", "configs", "logs", ".ddev/replay caches", "failure artifacts"]})
    write_json(args.out_dir / "summary.json", summary)
    write_json(args.out_dir / "targets.json", rows)
    write_json(args.out_dir / "failure-categories.json", categories)
    write_json(args.out_dir / "property-results.json", property_results)
    write_json(args.out_dir / "findings.json", findings)
    write_json(args.out_dir / "coverage-summary.json", coverages)

    write_tsv(args.out_dir / "summary.tsv", [summary], list(summary.keys()))
    write_tsv(args.out_dir / "targets.tsv", rows, ["status", "category", "category_label", "integration", "environment", "target", "fixture_ref", "target_ref", "failing_property_count", "summary"])
    write_tsv(args.out_dir / "failure-categories.tsv", categories, ["category", "label", "count", "description"])
    write_tsv(args.out_dir / "findings.tsv", findings, ["level", "property", "check", "integration", "environment", "target", "metric", "tag_key", "path", "message", "query"])
    write_tsv(args.out_dir / "coverage-summary.tsv", coverages, ["property", "integration", "environment", "target", "endpoint_count", "endpoint_emitted_count", "endpoint_missing_count", "endpoint_to_emitted_coverage", "metadata_count", "metadata_emitted_count", "metadata_unemitted_count", "metadata_to_emitted_coverage"])

    write_zip(args.zip, args.out_dir)
    print(markdown)


if __name__ == "__main__":
    main()
