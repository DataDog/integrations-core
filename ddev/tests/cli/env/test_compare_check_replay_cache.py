# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ddev.cli.env.compare_check import (
    REPLAY_CACHE_VERSION,
    _cache_file_names,
    _copy_fixture_bundle,
    _file_sha256,
    _is_suitable_replay_cache,
    _iter_replay_cache_candidates,
    _required_cache_files,
)

pbt_settings = settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])

safe_text = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters=['\x00']),
    max_size=80,
)
non_empty_safe_text = safe_text.filter(bool)
comparison_modes = st.sampled_from(['same-fixture-replay', 'record-each-side'])


def _write_cache_file(cache_dir: Path, name: str, content: str | None = None) -> None:
    path = cache_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(name if content is None else content)


def _write_valid_cache(
    cache_dir: Path,
    *,
    integration: str = 'cilium',
    adapter: str = 'requests',
    old_hatch_env: str = 'py3.13-1.9',
    new_hatch_env: str = 'py3.13-1.9',
    comparison_mode: str = 'same-fixture-replay',
    fixture_env: str | None = 'py3.13-1.9',
    old_head: str = 'old-head',
    new_head: str = 'new-head',
    check_class: str | None = None,
) -> dict:
    for name in _required_cache_files(comparison_mode):
        _write_cache_file(cache_dir, name)

    cache_files = _cache_file_names(cache_dir, comparison_mode)
    fixture_key = {
        'version': 1,
        'cache_version': REPLAY_CACHE_VERSION,
        'integration': integration,
        'adapter': adapter,
        'comparison_mode': comparison_mode,
        'fixture_env': fixture_env,
        'old_env': old_hatch_env,
        'new_env': new_hatch_env,
        'record_old_head': old_head,
        'record_new_head': new_head if comparison_mode == 'record-each-side' else None,
        'check_class': check_class,
        'files': {name: _file_sha256(cache_dir / name) for name in cache_files},
    }
    refs = {'fixture_key': fixture_key}
    (cache_dir / 'refs.json').write_text(json.dumps(refs, indent=2, sort_keys=True) + '\n')
    return refs


def test_cache_file_names_accepts_legacy_list_capture(tmp_path):
    _write_cache_file(tmp_path, 'config.json')
    (tmp_path / 'capture.json').write_text('[]')

    assert _cache_file_names(tmp_path, 'same-fixture-replay') == ['config.json', 'capture.json']


def test_copy_fixture_bundle_accepts_legacy_list_capture(tmp_path):
    cache_dir = tmp_path / 'cache'
    run_dir = tmp_path / 'run'
    cache_dir.mkdir()
    run_dir.mkdir()
    (cache_dir / 'capture.json').write_text('[]')

    _copy_fixture_bundle(cache_dir, run_dir, 'capture.json')

    assert (run_dir / 'capture.json').read_text() == '[]'


@pbt_settings
@given(comparison_mode=comparison_modes)
def test_required_cache_files_by_comparison_mode(comparison_mode):
    required = _required_cache_files(comparison_mode)

    if comparison_mode == 'same-fixture-replay':
        assert required == ['config.json', 'capture.json']
    else:
        assert required == ['old.config.json', 'capture.json', 'new.config.json', 'new.capture.json']


@pbt_settings
@given(comparison_mode=comparison_modes)
def test_suitable_replay_cache_accepts_matching_fixture_key(tmp_path, comparison_mode):
    fixture_env = 'py3.13-1.9' if comparison_mode == 'same-fixture-replay' else None
    _write_valid_cache(tmp_path, comparison_mode=comparison_mode, fixture_env=fixture_env)

    assert _is_suitable_replay_cache(
        tmp_path,
        integration='cilium',
        adapter='requests',
        old_hatch_env='py3.13-1.9',
        new_hatch_env='py3.13-1.9',
        comparison_mode=comparison_mode,
        fixture_env=fixture_env,
        old_head='old-head',
        new_head='new-head',
        check_class=None,
    )


@pbt_settings
@given(comparison_mode=comparison_modes)
def test_suitable_replay_cache_rejects_missing_required_files(tmp_path, comparison_mode):
    fixture_env = 'py3.13-1.9' if comparison_mode == 'same-fixture-replay' else None
    _write_valid_cache(tmp_path, comparison_mode=comparison_mode, fixture_env=fixture_env)

    for name in _required_cache_files(comparison_mode):
        case_dir = tmp_path / name.replace('.', '_')
        _write_valid_cache(case_dir, comparison_mode=comparison_mode, fixture_env=fixture_env)
        (case_dir / name).unlink()

        assert not _is_suitable_replay_cache(
            case_dir,
            integration='cilium',
            adapter='requests',
            old_hatch_env='py3.13-1.9',
            new_hatch_env='py3.13-1.9',
            comparison_mode=comparison_mode,
            fixture_env=fixture_env,
            old_head='old-head',
            new_head='new-head',
            check_class=None,
        )


@pbt_settings
@given(
    comparison_mode=comparison_modes,
    field=st.sampled_from(
        [
            'version',
            'cache_version',
            'integration',
            'adapter',
            'comparison_mode',
            'fixture_env',
            'old_env',
            'new_env',
            'record_old_head',
            'record_new_head',
            'check_class',
        ]
    ),
    replacement=non_empty_safe_text,
)
def test_suitable_replay_cache_rejects_fixture_key_mismatch(tmp_path, comparison_mode, field, replacement):
    fixture_env = 'py3.13-1.9' if comparison_mode == 'same-fixture-replay' else None
    refs = _write_valid_cache(tmp_path, comparison_mode=comparison_mode, fixture_env=fixture_env)
    original = refs['fixture_key'].get(field)
    assume_replacement = replacement
    if field == 'version':
        assume_replacement = 2
    elif field == 'cache_version':
        assume_replacement = REPLAY_CACHE_VERSION + 1
    elif original == replacement:
        assume_replacement = f'{replacement}-changed'

    refs['fixture_key'][field] = assume_replacement
    (tmp_path / 'refs.json').write_text(json.dumps(refs, indent=2, sort_keys=True) + '\n')

    assert not _is_suitable_replay_cache(
        tmp_path,
        integration='cilium',
        adapter='requests',
        old_hatch_env='py3.13-1.9',
        new_hatch_env='py3.13-1.9',
        comparison_mode=comparison_mode,
        fixture_env=fixture_env,
        old_head='old-head',
        new_head='new-head',
        check_class=None,
    )


@pbt_settings
@given(comparison_mode=comparison_modes, changed_content=non_empty_safe_text)
def test_suitable_replay_cache_rejects_file_hash_mismatch(tmp_path, comparison_mode, changed_content):
    fixture_env = 'py3.13-1.9' if comparison_mode == 'same-fixture-replay' else None
    _write_valid_cache(tmp_path, comparison_mode=comparison_mode, fixture_env=fixture_env)
    target_file = _required_cache_files(comparison_mode)[0]
    (tmp_path / target_file).write_text(f'changed:{changed_content}')

    assert not _is_suitable_replay_cache(
        tmp_path,
        integration='cilium',
        adapter='requests',
        old_hatch_env='py3.13-1.9',
        new_hatch_env='py3.13-1.9',
        comparison_mode=comparison_mode,
        fixture_env=fixture_env,
        old_head='old-head',
        new_head='new-head',
        check_class=None,
    )


def test_replay_cache_candidates_prefer_newest_suitable_directory(tmp_path):
    cache_root = tmp_path / 'cache-root'
    cache_root.mkdir()
    older = cache_root / '20260523-100000-old'
    newer = cache_root / '20260523-110000-new'
    older.mkdir()
    newer.mkdir()
    (cache_root / 'latest.txt').write_text(str(older))

    _write_valid_cache(older)
    _write_valid_cache(newer)

    older_mtime = 1_000_000_000
    newer_mtime = older_mtime + 10
    older.touch()
    newer.touch()
    os.utime(older, (older_mtime, older_mtime))
    os.utime(newer, (newer_mtime, newer_mtime))

    assert _iter_replay_cache_candidates(cache_root)[0] == newer.resolve()
