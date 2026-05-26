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
    if "metadata.csv" in haystack or "metadata" in haystack and ("missing" in haystack or "unemitted" in haystack):
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
        names = [short_test_name(str(item)) for item in failed_tests[:3]]
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
        property_results.append(
            {
                "target": target_slug(target),
                "integration": target.get("integration", ""),
                "environment": target.get("environment", ""),
                "property": property_name,
                "status": manifest.get("status", ""),
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


def pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{number * 100:.1f}%"


def bar(count: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "░" * width
    filled = int(round(width * count / total))
    return "█" * filled + "░" * (width - filled)


def md_escape(text: Any) -> str:
    return sanitize_text(text, max_len=MAX_DETAIL_TEXT).replace("|", "\\|")


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
        "## How this Replay PBT job works",
        "",
        "This POC compares a check's behavior against a replay cache, then mutates replay inputs to verify properties such as determinism, metadata consistency, and OpenMetrics coverage.",
        "",
        "```mermaid",
        "flowchart LR",
        f"  A[\"1. Build target matrix<br/>{counts['targets']} target result(s)\"] --> B[\"2. Restore or seed replay cache<br/>{counts['cache_ready']} ready / {counts['cache_blocked']} blocked\"]",
        "  B --> C[\"3. Run no-Agent replay<br/>same fixture, target ref\"]",
        f"  C --> D[\"4. Check replay properties<br/>{counts['replay_passed']} passed / {counts['replay_failed']} failed / {counts['replay_not_run']} not run\"]",
        f"  D --> E[\"5. Collect lightweight findings<br/>{counts['artifact_targets']} targets, {counts['findings']} findings, {counts['coverage_reports']} coverage reports\"]",
        "  E --> F[\"6. Build report bundle<br/>Markdown + HTML + JSON/TSV\"]",
        "```",
        "",
        "| Step | What happens | Result in this shard |",
        "|---|---|---:|",
        f"| 1. Matrix | Select integration/environment targets for this shard. | {counts['targets']} result file(s) |",
        f"| 2. Cache | Restore a replay cache or seed one with compare-check. | {counts['cache_ready']} ready, {counts['cache_blocked']} blocked/skipped |",
        f"| 3–4. Replay properties | Run replay-PBT properties against the cached fixture. | {counts['replay_passed']} passed, {counts['replay_failed']} failed, {counts['replay_not_run']} not run |",
        f"| 5. Findings | Copy only allowlisted lightweight findings/coverage JSON. | {counts['findings']} findings, {counts['coverage_reports']} coverage reports |",
        "| 6. Report | Generate this human summary and a sanitized report zip. | complete |",
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
) -> str:
    status_counts = Counter(row["status"] for row in rows)
    category_counts = Counter(row["category"] for row in rows if row["category"] != "passed")
    total = len(rows)
    passed = status_counts.get("passed", 0)
    failed = total - passed

    lines: list[str] = []
    lines.extend(
        [
            "# Replay PBT report",
            "",
            f"**Result:** {'✅ Passed' if failed == 0 and total else '❌ Needs attention'}  ",
            f"**Mode:** `{mode}`  ",
            f"**Shard:** `{shard}`  ",
            f"**Targets in matrix:** `{target_count}`  ",
            f"**Result files collected:** `{total}`",
            "",
            *build_replay_flow_markdown(rows, findings, coverages),
        ]
    )
    if shard_runs:
        lines.extend(["## Shard runs", "", "| Shard run | Conclusion | Link |", "|---|---|---|"])
        for run in shard_runs:
            run_id = md_escape(run.get("run_id", ""))
            title = md_escape(run.get("display_title", ""))
            conclusion = md_escape(run.get("conclusion", ""))
            url = md_escape(run.get("url", ""))
            lines.append(f"| `{run_id}` {title} | `{conclusion}` | [run]({url}) |")
        lines.append("")
    lines.extend(
        [
            "## Overview",
            "",
            "| Status | Count | Distribution |",
            "|---|---:|---|",
        ]
    )
    for status, count in sorted(status_counts.items(), key=lambda item: (-item[1], item[0])):
        icon = "✅" if status == "passed" else "❌" if status == "failed" else "🧱" if status == "failed-before-replay-pbt" else "⏭️"
        lines.append(f"| {icon} `{status}` | {count} | `{bar(count, total)}` |")
    lines.append("")
    if status_counts:
        lines.extend(["```mermaid", "pie title Replay PBT target status"])
        for status, count in sorted(status_counts.items()):
            lines.append(f'  "{status}" : {count}')
        lines.extend(["```", ""])

    lines.extend(["## Failure categories", ""])
    if category_counts:
        lines.extend(["| Category | Count | What it means | Examples |", "|---|---:|---|---|"])
        examples_by_category: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            if row["category"] != "passed" and len(examples_by_category[row["category"]]) < 4:
                examples_by_category[row["category"]].append(f"`{row['target']}`")
        for category, count in category_counts.most_common():
            icon, label, description = CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS["unknown"])
            examples = ", ".join(examples_by_category[category])
            lines.append(f"| {icon} {label} | {count} | {description} | {examples} |")
    else:
        lines.append("No failures reported.")
    lines.append("")

    actionable_findings = [f for f in findings if (f.get("level") or "").lower() in {"error", "warning", "warn"}]
    lines.extend(["## Top actionable property findings", ""])
    if actionable_findings:
        lines.extend(["| Target | Check | Metric/tag | Path | Message |", "|---|---|---|---|---|"])
        for finding in actionable_findings[:25]:
            metric = finding.get("metric") or finding.get("tag_key") or ""
            lines.append(
                f"| `{finding.get('target', '')}` | `{md_escape(finding.get('check', ''))}` | `{md_escape(metric)}` | `{md_escape(finding.get('path', ''))}` | {md_escape(finding.get('message', ''))} |"
            )
        if len(actionable_findings) > 25:
            lines.append(f"\n_… {len(actionable_findings) - 25} more findings in the report bundle._")
    else:
        lines.append("No actionable property findings collected.")
    lines.append("")

    lines.extend(["## OpenMetrics coverage", ""])
    if coverages:
        lines.extend(["| Target | Endpoint → emitted | metadata.csv → emitted | Endpoint count | Metadata count |", "|---|---:|---:|---:|---:|"])
        sorted_coverages = sorted(
            coverages,
            key=lambda c: (
                -1 if c.get("endpoint_to_emitted_coverage") is None else float(c.get("endpoint_to_emitted_coverage") or 0),
                c.get("target", ""),
            ),
            reverse=True,
        )
        for coverage in sorted_coverages[:30]:
            lines.append(
                f"| `{coverage.get('target', '')}` | {pct(coverage.get('endpoint_to_emitted_coverage'))} | {pct(coverage.get('metadata_to_emitted_coverage'))} | {coverage.get('endpoint_count') or ''} | {coverage.get('metadata_count') or ''} |"
            )
        if len(coverages) > 30:
            lines.append(f"\n_… {len(coverages) - 30} more coverage rows in the report bundle._")
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
            lines.append("| Target | Fixture | Failing properties | Summary |")
            lines.append("|---|---|---:|---|")
            for row in grouped_rows[:80]:
                lines.append(
                    f"| `{row['target']}` | `{md_escape(row.get('fixture_ref', ''))}` | {row.get('failing_property_count', 0)} | {md_escape(row.get('summary', ''))} |"
                )
            if len(grouped_rows) > 80:
                lines.append(f"| _… {len(grouped_rows) - 80} more_ | | | |")
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
) -> str:
    status_counts = Counter(row["status"] for row in rows)
    category_counts = Counter(row["category"] for row in rows if row["category"] != "passed")
    counts = replay_step_counts(rows, findings, coverages)
    artifact_targets = {finding.get("target") for finding in findings if finding.get("target")}
    artifact_targets.update(coverage.get("target") for coverage in coverages if coverage.get("target"))
    total = len(rows) or 1
    bars = "".join(
        f"<div><strong>{html.escape(status)}</strong> {count}<div class='bar'><span style='width:{100*count/total:.1f}%'></span></div></div>"
        for status, count in status_counts.most_common()
    )
    steps = [
        ("1", "Target matrix", f"{counts['targets']} target results", "Select integration/environment targets for this shard.", "ok"),
        ("2", "Replay cache", f"{counts['cache_ready']} ready · {counts['cache_blocked']} blocked", "Restore a cache or seed one with compare-check.", "warn" if counts['cache_blocked'] else "ok"),
        ("3", "No-Agent replay", "recorded fixture → target ref", "Run the check without a live Agent against replayed adapter input.", "ok"),
        ("4", "Property checks", f"{counts['replay_passed']} passed · {counts['replay_failed']} failed · {counts['replay_not_run']} not run", "Check determinism, cache mutations, metadata contracts, and coverage.", "fail" if counts['replay_failed'] else "ok"),
        ("5", "Findings", f"{counts['findings']} findings · {counts['coverage_reports']} coverage reports", "Collect only lightweight allowlisted JSON findings and coverage.", "warn" if counts['findings'] else "ok"),
        ("6", "Report", "HTML + Markdown + JSON/TSV zip", "Create a sanitized report bundle for the workflow results.", "ok"),
    ]
    step_cards = "".join(
        f"<section class='step {state}'><div class='step-num'>{num}</div><h3>{html.escape(title)}</h3><p class='metric'>{html.escape(metric)}</p><p>{html.escape(desc)}</p></section>"
        for num, title, metric, desc, state in steps
    )
    target_row_parts = []
    for row in rows:
        pipeline = ''.join(
            f'<span class="pill {state}">{html.escape(label)}: {html.escape(state)}</span>'
            for label, state in target_step_state(row, artifact_targets)
        )
        shard_link = f'<a href="{html.escape(str(row.get("run_url", "")))}">shard</a>' if row.get('run_url') else ''
        target_row_parts.append(
            "<tr>"
            f"<td><code>{html.escape(row['target'])}</code></td>"
            f"<td>{pipeline}</td>"
            f"<td>{html.escape(row['status'])}</td>"
            f"<td>{html.escape(row['category_label'])}</td>"
            f"<td>{html.escape(row['summary'])}</td>"
            f"<td>{shard_link}</td>"
            "</tr>"
        )
    target_rows = ''.join(target_row_parts)
    shard_rows = "".join(
        f"<tr><td><code>{html.escape(str(run.get('run_id', '')))}</code></td><td>{html.escape(str(run.get('display_title', '')))}</td><td>{html.escape(str(run.get('conclusion', '')))}</td><td><a href='{html.escape(str(run.get('url', '')))}'>run</a></td></tr>"
        for run in (shard_runs or [])
    )
    shard_card = f"<div class='card'><h2>Shard runs</h2><table><thead><tr><th>Run ID</th><th>Title</th><th>Conclusion</th><th>Link</th></tr></thead><tbody>{shard_rows}</tbody></table></div>" if shard_rows else ""
    category_rows = "".join(
        f"<tr><td>{html.escape(CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS['unknown'])[0])} {html.escape(CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS['unknown'])[1])}</td><td>{count}</td><td>{html.escape(CATEGORY_DEFINITIONS.get(category, CATEGORY_DEFINITIONS['unknown'])[2])}</td></tr>"
        for category, count in category_counts.most_common()
    )
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Replay PBT report</title>
<style>
:root{{--ok:#1f883d;--fail:#cf222e;--warn:#bf8700;--muted:#6e7781;--line:#d0d7de;--bg:#f6f8fa;--purple:#8250df}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:2rem;line-height:1.45;color:#1f2328;background:white}}
.hero{{background:linear-gradient(135deg,#f6f8ff,#fff);border:1px solid var(--line);border-radius:16px;padding:1.5rem;margin-bottom:1rem}}
.card{{border:1px solid var(--line);border-radius:12px;padding:1rem;margin:1rem 0;background:var(--bg)}}
.flow{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:.75rem;margin:1rem 0}}
.step{{position:relative;border:1px solid var(--line);border-radius:14px;padding:1rem;background:white;box-shadow:0 1px 2px rgba(31,35,40,.06)}}
.step:after{{content:'→';position:absolute;right:-.65rem;top:45%;color:var(--muted);font-weight:700}}
.step:last-child:after{{content:''}}
.step.ok{{border-top:5px solid var(--ok)}}.step.fail{{border-top:5px solid var(--fail)}}.step.warn{{border-top:5px solid var(--warn)}}
.step-num{{width:2rem;height:2rem;border-radius:999px;background:#eef2ff;color:var(--purple);display:grid;place-items:center;font-weight:700}}
.step h3{{margin:.55rem 0 .15rem}}.metric{{font-weight:700;margin:.25rem 0;color:#24292f}}
.bar{{height:12px;background:#eaeef2;border-radius:999px;overflow:hidden;margin:.25rem 0 1rem}}
.bar span{{display:block;height:100%;background:var(--purple)}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border:1px solid var(--line);padding:.45rem;text-align:left;vertical-align:top}}th{{background:var(--bg)}}
code{{background:var(--bg);padding:.1rem .25rem;border-radius:4px}}
.pill{{display:inline-block;border-radius:999px;padding:.12rem .45rem;margin:.1rem;font-size:12px;border:1px solid var(--line)}}
.pill.ok{{background:#dafbe1;color:#116329;border-color:#aceebb}}.pill.fail{{background:#ffebe9;color:#82071e;border-color:#ffcecb}}.pill.warn,.pill.blocked{{background:#fff8c5;color:#633c01;border-color:#fae17d}}.pill.skipped,.pill.none{{background:#f6f8fa;color:#57606a}}.pill.blocked{{background:#fff8c5}}pre{{white-space:pre-wrap;max-height:35rem;overflow:auto}}
</style></head><body>
<div class='hero'><h1>Replay PBT workflow results</h1><p>This report explains the workflow pipeline and shows which step each target reached.</p></div>
<div class='card'><h2>Workflow flow</h2><div class='flow'>{step_cards}</div></div>
{shard_card}
<div class='card'><h2>Status distribution</h2>{bars}</div>
<div class='card'><h2>Failure categories</h2><table><thead><tr><th>Category</th><th>Count</th><th>Meaning</th></tr></thead><tbody>{category_rows or '<tr><td colspan="3">No failures</td></tr>'}</tbody></table></div>
<div class='card'><h2>Targets by workflow step</h2><table><thead><tr><th>Target</th><th>Pipeline state</th><th>Status</th><th>Category</th><th>Summary</th><th>Shard run</th></tr></thead><tbody>{target_rows}</tbody></table></div>
<div class='card'><h2>Markdown source</h2><pre>{html.escape(markdown[:20000])}</pre></div>
</body></html>"""


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
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_results(args.results)
    property_results, findings, coverages = load_findings_and_coverages(args.findings)

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

    markdown = build_markdown(rows, findings, coverages, mode=args.mode, shard=args.shard, target_count=args.target_count)
    html_report = build_html(markdown, rows, findings, coverages)

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
