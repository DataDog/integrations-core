#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Build a cross-run flake report from Replay validation report bundles.

This script compares multiple replay-pbt report artifacts produced from the same
branch/SHA and replay configuration. It is intentionally based on the sanitized
report bundles (`replay-pbt-report.zip`), not raw replay caches.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ReportInput:
    label: str
    run_id: str
    run_url: str
    report_dir: Path


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    lines = ['\t'.join(fields)]
    for row in rows:
        lines.append('\t'.join(str(row.get(field, '')).replace('\t', ' ').replace('\n', ' ') for field in fields))
    path.write_text('\n'.join(lines) + '\n')


def md_escape(value: Any) -> str:
    return str(value).replace('|', '\\|').replace('\n', '<br/>')


def gh_json(api_path: str) -> Any:
    result = subprocess.run(['gh', 'api', api_path], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def download_report_artifact(run_id: str, destination: Path) -> tuple[Path, str, str]:
    artifacts = gh_json(f'repos/DataDog/integrations-core/actions/runs/{run_id}/artifacts?per_page=100')['artifacts']
    matches = [artifact for artifact in artifacts if artifact.get('name') == 'replay-pbt-report']
    if not matches:
        raise RuntimeError(f'Run {run_id} has no replay-pbt-report artifact')
    artifact = matches[0]
    archive = destination / f'{run_id}-replay-pbt-report-artifact.zip'
    with archive.open('wb') as f:
        subprocess.run(['gh', 'api', artifact['archive_download_url']], stdout=f, check=True)
    run = gh_json(f'repos/DataDog/integrations-core/actions/runs/{run_id}')
    return archive, str(run.get('html_url', '')), str(run.get('display_title', run_id))


def extract_report_archive(archive: Path, destination: Path) -> Path:
    """Extract a report archive and return the directory containing targets.json."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(destination)

    if (destination / 'targets.json').is_file():
        return destination

    # GitHub artifact downloads are often an outer zip containing replay-pbt-report.zip.
    inner_zips = sorted(destination.glob('*.zip'))
    for inner in inner_zips:
        inner_dir = destination / inner.stem
        inner_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(inner) as zf:
            zf.extractall(inner_dir)
        if (inner_dir / 'targets.json').is_file():
            return inner_dir

    candidates = list(destination.glob('**/targets.json'))
    if candidates:
        return candidates[0].parent
    raise RuntimeError(f'{archive} did not contain a Replay validation report')


def prepare_report_inputs(args: argparse.Namespace, tmpdir: Path) -> list[ReportInput]:
    reports: list[ReportInput] = []

    for run_id in [item.strip() for item in (args.run_ids or '').split(',') if item.strip()]:
        archive, run_url, title = download_report_artifact(run_id, tmpdir)
        report_dir = extract_report_archive(archive, tmpdir / f'run-{run_id}')
        reports.append(ReportInput(label=title or run_id, run_id=run_id, run_url=run_url, report_dir=report_dir))

    for index, item in enumerate(args.reports or [], start=1):
        path = Path(item)
        label = path.stem
        report_dir: Path
        if path.is_dir():
            report_dir = path
            if not (report_dir / 'targets.json').is_file():
                candidates = list(path.glob('**/targets.json'))
                if not candidates:
                    raise RuntimeError(f'{path} is not a Replay validation report directory')
                report_dir = candidates[0].parent
        elif path.is_file() and path.suffix == '.zip':
            report_dir = extract_report_archive(path, tmpdir / f'input-{index}')
        else:
            raise RuntimeError(f'Unsupported report input: {path}')
        reports.append(ReportInput(label=label, run_id=f'local-{index}-{label}', run_url='', report_dir=report_dir))

    if len(reports) < 2:
        raise SystemExit('Need at least two reports or run IDs to detect flakes')
    return reports


def target_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get('target') or f"{row.get('integration', '')}:{row.get('environment', '')}"),
        str(row.get('fixture_ref', '')),
        str(row.get('target_ref', '')),
        str(row.get('readings', '')),
        str(row.get('adapters', '')),
    )


def property_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get('target', '')), str(row.get('property', '')))


def finding_fingerprint(row: dict[str, Any]) -> str:
    fields = [
        'property',
        'check',
        'level',
        'collection',
        'metric',
        'tag_key',
        'path',
        'message',
        'query',
        'submission_type',
        'metadata_type',
    ]
    return json.dumps({field: row.get(field, '') for field in fields}, sort_keys=True)


def summarize_reports(reports: list[ReportInput]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    target_observations: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    property_observations: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    finding_observations: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    run_rows = []
    for report in reports:
        targets = [row for row in load_json(report.report_dir / 'targets.json', []) if isinstance(row, dict)]
        properties = [row for row in load_json(report.report_dir / 'property-results.json', []) if isinstance(row, dict)]
        findings = [row for row in load_json(report.report_dir / 'findings.json', []) if isinstance(row, dict)]
        summary = load_json(report.report_dir / 'summary.json', {})
        run_rows.append(
            {
                'run_id': report.run_id,
                'label': report.label,
                'url': report.run_url,
                'target_count': len(targets),
                'status_counts': summary.get('status_counts', {}),
            }
        )
        for row in targets:
            enriched = dict(row, run_id=report.run_id, run_url=report.run_url, run_label=report.label)
            target_observations[target_key(enriched)].append(enriched)
        for row in properties:
            enriched = dict(row, run_id=report.run_id, run_url=report.run_url, run_label=report.label)
            property_observations[property_key(enriched)].append(enriched)
        for row in findings:
            enriched = dict(row, run_id=report.run_id, run_url=report.run_url, run_label=report.label)
            finding_observations[property_key(enriched)].append(enriched)

    expected_runs = {report.run_id for report in reports}
    target_rows = []
    for key, observations in sorted(target_observations.items()):
        observed_runs = {row['run_id'] for row in observations}
        statuses = sorted({str(row.get('status', 'unknown')) for row in observations})
        categories = sorted({str(row.get('category', 'unknown')) for row in observations})
        summaries = sorted({str(row.get('summary', '')) for row in observations if row.get('summary')})
        missing_runs = sorted(expected_runs - observed_runs)
        cache_keys = sorted({str(row.get('cache_key', '')) for row in observations})
        flaky = len(statuses) > 1 or len(categories) > 1 or len(cache_keys) > 1 or bool(missing_runs)
        target_rows.append(
            {
                'target': key[0],
                'fixture_ref': key[1],
                'target_ref': key[2],
                'readings': key[3],
                'adapters': key[4],
                'cache_key': ','.join(cache_keys),
                'runs_observed': len(observed_runs),
                'runs_expected': len(expected_runs),
                'statuses': ','.join(statuses),
                'categories': ','.join(categories),
                'missing_runs': ','.join(missing_runs),
                'summaries': ' | '.join(summaries[:5]),
                'flake_kind': 'target-status' if len(statuses) > 1 or len(categories) > 1 else 'cache-key' if len(cache_keys) > 1 else 'missing-target' if missing_runs else 'stable-target',
                'flaky': flaky,
            }
        )

    property_rows = []
    for (target, prop), observations in sorted(property_observations.items()):
        statuses = sorted({str(row.get('status', 'unknown')) for row in observations})
        observed_runs = {row['run_id'] for row in observations}
        missing_runs = sorted(expected_runs - observed_runs)
        flaky = len(statuses) > 1 or bool(missing_runs)
        property_rows.append(
            {
                'target': target,
                'property': prop,
                'runs_observed': len(observed_runs),
                'runs_expected': len(expected_runs),
                'statuses': ','.join(statuses),
                'missing_runs': ','.join(missing_runs),
                'flake_kind': 'property-status' if flaky else 'stable-property',
                'flaky': flaky,
            }
        )

    finding_rows = []
    for (target, prop), observations in sorted(finding_observations.items()):
        fingerprints_by_run: dict[str, set[str]] = defaultdict(set)
        for row in observations:
            fingerprints_by_run[row['run_id']].add(finding_fingerprint(row))
        fingerprint_sets = {run_id: sorted(values) for run_id, values in fingerprints_by_run.items()}
        distinct_sets = {json.dumps(values, sort_keys=True) for values in fingerprint_sets.values()}
        missing_runs = sorted(expected_runs - set(fingerprint_sets))
        flaky = len(distinct_sets) > 1 or bool(missing_runs)
        finding_rows.append(
            {
                'target': target,
                'property': prop,
                'runs_with_findings': len(fingerprint_sets),
                'runs_expected': len(expected_runs),
                'distinct_finding_sets': len(distinct_sets),
                'missing_runs': ','.join(missing_runs),
                'flake_kind': 'finding-fingerprint' if flaky else 'stable-finding',
                'flaky': flaky,
            }
        )

    return run_rows, target_rows, property_rows, finding_rows


def write_markdown(
    path: Path,
    run_rows: list[dict[str, Any]],
    target_rows: list[dict[str, Any]],
    property_rows: list[dict[str, Any]],
    finding_rows: list[dict[str, Any]],
) -> None:
    flaky_targets = [row for row in target_rows if row['flaky']]
    flaky_properties = [row for row in property_rows if row['flaky']]
    flaky_findings = [row for row in finding_rows if row['flaky']]
    status = '❌ Flakes detected' if (flaky_targets or flaky_properties or flaky_findings) else '✅ No flakes detected'
    lines = [
        '# Replay validation flake report',
        '',
        f'**Result:** {status}',
        f'**Compared reports:** `{len(run_rows)}`',
        f'**Generated at:** `{datetime.now(timezone.utc).isoformat()}`',
        '',
        '## Runs compared',
        '',
        '| Run | Targets | Status counts |',
        '|---|---:|---|',
    ]
    for row in run_rows:
        label = f"[{row['run_id']}]({row['url']})" if row.get('url') else f"`{row['run_id']}`"
        lines.append(f"| {label} | {row.get('target_count', 0)} | `{md_escape(json.dumps(row.get('status_counts', {}), sort_keys=True))}` |")

    lines.extend(
        [
            '',
            '## Flaky target outcomes',
            '',
        ]
    )
    if flaky_targets:
        lines.extend(['| Target | Statuses | Categories | Missing runs | Cache key |', '|---|---|---|---|---|'])
        for row in flaky_targets[:200]:
            lines.append(
                f"| `{md_escape(row['target'])}` | `{md_escape(row['statuses'])}` | `{md_escape(row['categories'])}` | "
                f"`{md_escape(row['missing_runs'])}` | `{md_escape(row['cache_key'])}` |"
            )
    else:
        lines.append('No target-level status/category flakes detected.')

    lines.extend(['', '## Flaky property outcomes', ''])
    if flaky_properties:
        lines.extend(['| Target | Property | Statuses | Missing runs |', '|---|---|---|---|'])
        for row in flaky_properties[:200]:
            lines.append(
                f"| `{md_escape(row['target'])}` | `{md_escape(row['property'])}` | `{md_escape(row['statuses'])}` | `{md_escape(row['missing_runs'])}` |"
            )
    else:
        lines.append('No property-level pass/fail flakes detected.')

    lines.extend(['', '## Flaky finding fingerprints', ''])
    if flaky_findings:
        lines.extend(['| Target | Property | Distinct finding sets | Missing runs |', '|---|---|---:|---|'])
        for row in flaky_findings[:200]:
            lines.append(
                f"| `{md_escape(row['target'])}` | `{md_escape(row['property'])}` | {row['distinct_finding_sets']} | `{md_escape(row['missing_runs'])}` |"
            )
    else:
        lines.append('No finding-fingerprint flakes detected.')

    path.write_text('\n'.join(lines) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-ids', default='', help='Comma-separated Replay validation workflow run IDs to download')
    parser.add_argument('--reports', nargs='*', help='Local report directories or replay-pbt-report.zip files')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--zip', type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir_str:
        reports = prepare_report_inputs(args, Path(tmpdir_str))
        run_rows, target_rows, property_rows, finding_rows = summarize_reports(reports)

    summary = {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'report_count': len(run_rows),
        'target_count': len(target_rows),
        'flaky_target_count': sum(1 for row in target_rows if row['flaky']),
        'flaky_property_count': sum(1 for row in property_rows if row['flaky']),
        'flaky_finding_count': sum(1 for row in finding_rows if row['flaky']),
    }
    write_json(args.out_dir / 'summary.json', summary)
    write_json(args.out_dir / 'runs.json', run_rows)
    write_json(args.out_dir / 'target-flakes.json', target_rows)
    write_json(args.out_dir / 'property-flakes.json', property_rows)
    write_json(args.out_dir / 'finding-flakes.json', finding_rows)
    write_tsv(args.out_dir / 'target-flakes.tsv', target_rows, ['flaky', 'target', 'fixture_ref', 'target_ref', 'readings', 'adapters', 'cache_key', 'statuses', 'categories', 'missing_runs', 'summaries'])
    write_tsv(args.out_dir / 'property-flakes.tsv', property_rows, ['flaky', 'target', 'property', 'statuses', 'missing_runs'])
    write_tsv(args.out_dir / 'finding-flakes.tsv', finding_rows, ['flaky', 'target', 'property', 'distinct_finding_sets', 'missing_runs'])
    write_markdown(args.out_dir / 'report.md', run_rows, target_rows, property_rows, finding_rows)

    if args.zip:
        if args.zip.exists():
            args.zip.unlink()
        shutil.make_archive(str(args.zip.with_suffix('')), 'zip', args.out_dir)

    print((args.out_dir / 'report.md').read_text())


if __name__ == '__main__':
    main()
