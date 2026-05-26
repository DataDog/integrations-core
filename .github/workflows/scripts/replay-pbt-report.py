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


def build_markdown(rows: list[dict[str, Any]], findings: list[dict[str, Any]], coverages: list[dict[str, Any]], *, mode: str, shard: str, target_count: str) -> str:
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


def build_html(markdown: str, rows: list[dict[str, Any]], findings: list[dict[str, Any]], coverages: list[dict[str, Any]]) -> str:
    status_counts = Counter(row["status"] for row in rows)
    total = len(rows) or 1
    bars = "".join(
        f"<div><strong>{html.escape(status)}</strong> {count}<div class='bar'><span style='width:{100*count/total:.1f}%'></span></div></div>"
        for status, count in status_counts.most_common()
    )
    target_rows = "".join(
        f"<tr><td>{html.escape(row['target'])}</td><td>{html.escape(row['status'])}</td><td>{html.escape(row['category_label'])}</td><td>{html.escape(row['summary'])}</td></tr>"
        for row in rows
    )
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Replay PBT report</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:2rem;line-height:1.45;color:#1f2328}}
.card{{border:1px solid #d0d7de;border-radius:10px;padding:1rem;margin:1rem 0;background:#f6f8fa}}
.bar{{height:12px;background:#eaeef2;border-radius:999px;overflow:hidden;margin:.25rem 0 1rem}}
.bar span{{display:block;height:100%;background:#8250df}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border:1px solid #d0d7de;padding:.35rem;text-align:left;vertical-align:top}}th{{background:#f6f8fa}}
code{{background:#f6f8fa;padding:.1rem .25rem;border-radius:4px}}
</style></head><body>
<h1>Replay PBT report</h1>
<div class='card'><h2>Status distribution</h2>{bars}</div>
<div class='card'><h2>Targets</h2><table><thead><tr><th>Target</th><th>Status</th><th>Category</th><th>Summary</th></tr></thead><tbody>{target_rows}</tbody></table></div>
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
