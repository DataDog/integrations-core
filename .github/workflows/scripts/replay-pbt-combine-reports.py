#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Combine sanitized Replay PBT report bundles from multiple shard runs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def load_report_module(script_dir: Path):
    path = script_dir / 'replay-pbt-report.py'
    spec = importlib.util.spec_from_file_location('replay_pbt_report', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Unable to load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gh_json(api_path: str) -> Any:
    result = subprocess.run(['gh', 'api', api_path], text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def list_run_jobs(run_id: str) -> dict[str, str]:
    jobs = gh_json(f'repos/DataDog/integrations-core/actions/runs/{run_id}/jobs?per_page=100').get('jobs', [])
    return {str(job.get('name', '')): str(job.get('html_url', '')) for job in jobs if job.get('name') and job.get('html_url')}


def download_artifact(run_id: str, destination: Path) -> dict[str, Any]:
    artifacts = gh_json(f'repos/DataDog/integrations-core/actions/runs/{run_id}/artifacts?per_page=100')['artifacts']
    matches = [artifact for artifact in artifacts if artifact.get('name') == 'replay-pbt-report']
    if not matches:
        raise RuntimeError(f'Run {run_id} has no replay-pbt-report artifact')
    artifact = matches[0]
    archive = destination / f'{run_id}-artifact.zip'
    with archive.open('wb') as f:
        subprocess.run(['gh', 'api', artifact['archive_download_url']], stdout=f, check=True)
    run = gh_json(f'repos/DataDog/integrations-core/actions/runs/{run_id}')
    return {
        'run_id': run_id,
        'url': run.get('html_url', ''),
        'display_title': run.get('display_title', ''),
        'status': run.get('status', ''),
        'conclusion': run.get('conclusion', ''),
        'job_urls': list_run_jobs(run_id),
        'artifact_archive': archive,
    }


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return []


def dedupe(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen = set()
    output = []
    for row in rows:
        key = tuple(json.dumps(row.get(name, ''), sort_keys=True) for name in keys)
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def extract_inner_report(artifact_archive: Path, destination: Path) -> Path:
    outer = destination / 'outer'
    outer.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(artifact_archive) as zf:
        zf.extractall(outer)
    inner = outer / 'replay-pbt-report.zip'
    if not inner.is_file():
        candidates = list(outer.glob('*.zip'))
        if not candidates:
            raise RuntimeError(f'{artifact_archive} did not contain replay-pbt-report.zip')
        inner = candidates[0]
    report_dir = destination / 'report'
    report_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(inner) as zf:
        zf.extractall(report_dir)
    return report_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-ids', required=True, help='Comma-separated shard workflow run IDs')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--zip', type=Path, required=True)
    parser.add_argument('--mode', default='combined')
    parser.add_argument('--run-group', default='')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    report = load_report_module(script_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    run_ids = [item.strip() for item in args.run_ids.split(',') if item.strip()]
    if not run_ids:
        raise SystemExit('No run IDs provided')

    targets: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    coverages: list[dict[str, Any]] = []
    property_results: list[dict[str, Any]] = []
    shard_runs: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        for run_id in run_ids:
            run_info = download_artifact(run_id, tmpdir)
            shard_runs.append({k: v for k, v in run_info.items() if k not in {'artifact_archive', 'job_urls'}})
            report_dir = extract_inner_report(run_info['artifact_archive'], tmpdir / run_id)
            job_urls = run_info.get('job_urls', {})
            for row in read_json(report_dir / 'targets.json'):
                if isinstance(row, dict):
                    row.setdefault('run_id', run_id)
                    row.setdefault('run_url', run_info.get('url', ''))
                    row.setdefault('run_title', run_info.get('display_title', ''))
                    row.setdefault('job_url', job_urls.get(str(row.get('target', '')), ''))
                    targets.append(row)
            for row in read_json(report_dir / 'findings.json'):
                if isinstance(row, dict):
                    row.setdefault('run_id', run_id)
                    row.setdefault('run_url', run_info.get('url', ''))
                    row.setdefault('job_url', job_urls.get(str(row.get('target', '')), ''))
                    findings.append(row)
            for row in read_json(report_dir / 'coverage-summary.json'):
                if isinstance(row, dict):
                    row.setdefault('run_id', run_id)
                    row.setdefault('run_url', run_info.get('url', ''))
                    row.setdefault('job_url', job_urls.get(str(row.get('target', '')), ''))
                    coverages.append(row)
            for row in read_json(report_dir / 'property-results.json'):
                if isinstance(row, dict):
                    row.setdefault('run_id', run_id)
                    row.setdefault('run_url', run_info.get('url', ''))
                    row.setdefault('job_url', job_urls.get(str(row.get('target', '')), ''))
                    property_results.append(row)

    targets = dedupe(targets, ('target', 'status', 'category', 'run_id'))
    findings = dedupe(findings, ('target', 'property', 'check', 'metric', 'tag_key', 'path', 'message'))
    coverages = dedupe(coverages, ('target', 'property'))
    property_results = dedupe(property_results, ('target', 'property', 'status'))

    from collections import Counter
    from datetime import datetime, timezone

    status_counts = Counter(row.get('status', 'unknown') for row in targets)
    category_counts = Counter(row.get('category', 'unknown') for row in targets if row.get('category') != 'passed')
    summary = {
        'schema_version': 1,
        'combined': True,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'mode': args.mode,
        'run_group': args.run_group,
        'shard_runs': shard_runs,
        'result_files_collected': len(targets),
        'status_counts': dict(status_counts),
        'failure_category_counts': dict(category_counts),
        'property_result_count': len(property_results),
        'finding_count': len(findings),
        'coverage_count': len(coverages),
    }
    categories = [
        {
            'category': category,
            'label': report.CATEGORY_DEFINITIONS.get(category, report.CATEGORY_DEFINITIONS['unknown'])[1],
            'count': count,
            'description': report.CATEGORY_DEFINITIONS.get(category, report.CATEGORY_DEFINITIONS['unknown'])[2],
        }
        for category, count in category_counts.most_common()
    ]

    markdown = report.build_markdown(
        targets,
        findings,
        coverages,
        mode=args.mode,
        shard=f'combined {len(shard_runs)} shard runs',
        target_count=str(len(targets)),
        shard_runs=shard_runs,
        property_results=property_results,
    )
    html_report = report.build_html(markdown, targets, findings, coverages, shard_runs=shard_runs, property_results=property_results)

    (args.out_dir / 'report.md').write_text(markdown)
    (args.out_dir / 'report.html').write_text(html_report)
    report.write_json(args.out_dir / 'manifest.json', {'schema_version': 1, 'combined': True, 'allowlisted_files_only': True})
    report.write_json(args.out_dir / 'summary.json', summary)
    report.write_json(args.out_dir / 'targets.json', targets)
    report.write_json(args.out_dir / 'failure-categories.json', categories)
    report.write_json(args.out_dir / 'property-results.json', property_results)
    report.write_json(args.out_dir / 'findings.json', findings)
    report.write_json(args.out_dir / 'coverage-summary.json', coverages)
    report.write_tsv(args.out_dir / 'summary.tsv', [summary], [k for k in summary if k != 'shard_runs'])
    report.write_tsv(args.out_dir / 'targets.tsv', targets, ['status', 'category', 'category_label', 'integration', 'environment', 'target', 'fixture_ref', 'target_ref', 'failing_property_count', 'summary', 'run_id', 'run_url', 'job_url'])
    report.write_tsv(args.out_dir / 'failure-categories.tsv', categories, ['category', 'label', 'count', 'description'])
    report.write_tsv(args.out_dir / 'findings.tsv', findings, ['level', 'property', 'check', 'integration', 'environment', 'target', 'metric', 'tag_key', 'path', 'message', 'query', 'run_id', 'run_url', 'job_url'])
    report.write_tsv(args.out_dir / 'coverage-summary.tsv', coverages, ['property', 'integration', 'environment', 'target', 'endpoint_count', 'endpoint_emitted_count', 'endpoint_missing_count', 'endpoint_to_emitted_coverage', 'metadata_count', 'metadata_emitted_count', 'metadata_unemitted_count', 'metadata_to_emitted_coverage', 'run_id', 'run_url', 'job_url'])
    report.write_zip(args.zip, args.out_dir)
    print(markdown)


if __name__ == '__main__':
    main()
