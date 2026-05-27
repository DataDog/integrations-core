# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Probe-specific diffs for compare-agent artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def diff_freeze(record_path: Path, replay_path: Path) -> dict[str, Any]:
    """Diff two ``agent integration freeze`` outputs.

    Each line of the form ``datadog-<pkg>==<ver>`` is parsed into a
    package -> version map. The diff is `{added, removed, changed}` keyed
    by package name.
    """

    def _parse(p: Path) -> dict[str, str]:
        out: dict[str, str] = {}
        if not p.is_file():
            return out
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '==' not in line:
                continue
            if not line.startswith('datadog-'):
                continue
            pkg, _, ver = line.partition('==')
            out[pkg.strip()] = ver.strip()
        return out

    record = _parse(record_path)
    replay = _parse(replay_path)

    added = sorted(pkg for pkg in replay if pkg not in record)
    removed = sorted(pkg for pkg in record if pkg not in replay)
    changed = [
        {'package': pkg, 'record': record[pkg], 'replay': replay[pkg]}
        for pkg in sorted(record)
        if pkg in replay and record[pkg] != replay[pkg]
    ]

    return {
        'kind': 'freeze',
        'record_count': len(record),
        'replay_count': len(replay),
        'added': added,
        'removed': removed,
        'changed': changed,
        'equal': not (added or removed or changed),
    }


_INVENTORY_DROP_KEYS = frozenset({
    'last_execution_date',
    'last_run_duration',
    'last_run_finish',
    'last_run_start',
    'next_run',
    'check_id',  # contains random suffix; init_config_hash / instance_config_hash carry the meaningful identity
    'last_successful_execution_date',
    'last_successful_run',
    'last_run_status',
    'last_error',
    'agent_version',  # we report agent_version separately
    'install_method',
    'host_info',
    'timestamp',  # top-level payload timestamp
    'uuid',       # per-run UUID
})


def _normalize_inventory(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            k: _normalize_inventory(v)
            for k, v in sorted(payload.items())
            if k not in _INVENTORY_DROP_KEYS
        }
    if isinstance(payload, list):
        return sorted(
            (_normalize_inventory(v) for v in payload),
            key=lambda v: json.dumps(v, sort_keys=True),
        )
    return payload


def diff_inventory(record_path: Path, replay_path: Path) -> dict[str, Any]:
    """Diff two ``inventory-checks`` payloads after volatile-key stripping."""

    def _load(p: Path) -> Any:
        if not p.is_file():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None

    record = _normalize_inventory(_load(record_path))
    replay = _normalize_inventory(_load(replay_path))

    equal = json.dumps(record, sort_keys=True) == json.dumps(replay, sort_keys=True)
    return {
        'kind': 'inventory',
        'equal': equal,
        'record_present': record is not None,
        'replay_present': replay is not None,
        # We do not embed the full payloads in the diff to keep artifacts
        # small; consumers can read the normalized files alongside.
        'changed_check_names': _diff_inventory_check_names(record, replay),
    }


def _check_names(inv: Any) -> list[str]:
    if not isinstance(inv, dict):
        return []
    checks = inv.get('check_metadata') if isinstance(inv, dict) else None
    if not isinstance(checks, dict):
        return []
    return sorted(checks.keys())


def _diff_inventory_check_names(record: Any, replay: Any) -> dict[str, list[str]]:
    rc = set(_check_names(record))
    rp = set(_check_names(replay))
    return {
        'added': sorted(rp - rc),
        'removed': sorted(rc - rp),
        'shared': sorted(rc & rp),
    }


def diff_check(record_path: Path, replay_path: Path) -> dict[str, Any]:
    """Diff ``agent check --json`` aggregator output (light-weight schema-aware).

    The Agent emits a JSON array of instance results; each instance has
    ``aggregator`` (metrics, service_checks, events) and ``runner``. We
    reduce to a stable per-metric record set and diff multiset-style.
    """

    def _load_records(p: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not p.is_file():
            return [], []
        try:
            data = json.loads(p.read_text())
        except Exception:
            return [], []
        metrics: list[dict[str, Any]] = []
        service_checks: list[dict[str, Any]] = []
        if not isinstance(data, list):
            return metrics, service_checks
        for instance in data:
            agg = instance.get('aggregator') if isinstance(instance, dict) else None
            if not isinstance(agg, dict):
                continue
            for m in agg.get('metrics', []) or []:
                metrics.append({
                    'name': m.get('metric'),
                    'type': m.get('type'),
                    'tags': sorted(m.get('tags') or []),
                    'points_count': len(m.get('points') or []),
                    'host': m.get('host'),
                })
            for sc in agg.get('service_checks', []) or []:
                service_checks.append({
                    'name': sc.get('check'),
                    'status': sc.get('status'),
                    'tags': sorted(sc.get('tags') or []),
                })
        return metrics, service_checks

    rec_metrics, rec_scs = _load_records(record_path)
    rep_metrics, rep_scs = _load_records(replay_path)

    def _multiset_diff(a: list[dict[str, Any]], b: list[dict[str, Any]]):
        def _key(d):
            return json.dumps(d, sort_keys=True)
        from collections import Counter
        ca, cb = Counter(_key(x) for x in a), Counter(_key(x) for x in b)
        removed = [json.loads(k) for k, count in ca.items() for _ in range(max(0, count - cb.get(k, 0)))]
        added = [json.loads(k) for k, count in cb.items() for _ in range(max(0, count - ca.get(k, 0)))]
        return added, removed

    metrics_added, metrics_removed = _multiset_diff(rec_metrics, rep_metrics)
    sc_added, sc_removed = _multiset_diff(rec_scs, rep_scs)

    return {
        'kind': 'check',
        'metrics': {
            'record_count': len(rec_metrics),
            'replay_count': len(rep_metrics),
            'added': added_top(metrics_added),
            'removed': added_top(metrics_removed),
            'added_total': len(metrics_added),
            'removed_total': len(metrics_removed),
        },
        'service_checks': {
            'record_count': len(rec_scs),
            'replay_count': len(rep_scs),
            'added': sc_added,
            'removed': sc_removed,
        },
        'equal': not (metrics_added or metrics_removed or sc_added or sc_removed),
    }


def added_top(items: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    """Cap a diff list so artifacts stay small even on big regressions."""
    if len(items) <= limit:
        return items
    return items[:limit] + [{'_truncated': len(items) - limit}]


def write_diffs(run_dir: Path, summary: dict[str, Any]) -> dict[str, Any]:
    """Compute every probe diff using the per-role paths in ``summary``."""
    record_probes = summary.get('record', {}).get('probes', {})
    replay_probes = summary.get('replay', {}).get('probes', {})
    out: dict[str, Any] = {}

    if 'freeze' in record_probes and 'freeze' in replay_probes:
        d = diff_freeze(Path(record_probes['freeze']), Path(replay_probes['freeze']))
        (run_dir / 'freeze.diff.json').write_text(json.dumps(d, indent=2, sort_keys=True) + '\n')
        out['freeze'] = d

    if 'inventory' in record_probes and 'inventory' in replay_probes:
        d = diff_inventory(Path(record_probes['inventory']), Path(replay_probes['inventory']))
        (run_dir / 'inventory.diff.json').write_text(json.dumps(d, indent=2, sort_keys=True) + '\n')
        out['inventory'] = d

    if 'check' in record_probes and 'check' in replay_probes:
        d = diff_check(Path(record_probes['check']), Path(replay_probes['check']))
        (run_dir / 'check.diff.json').write_text(json.dumps(d, indent=2, sort_keys=True) + '\n')
        out['check'] = d

    return out
